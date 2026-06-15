from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from catalog.admin import CatalogChannelAdmin
from catalog.deactivation import DeactivationReason
from catalog.models import CatalogChannel, make_external_key, make_group_key
from catalog.normalize import fit_catalog_entry
from catalog.probe import filter_reachable_entries
from catalog.stream_urls import is_hls_stream_url
from catalog.sync import deactivate_non_hls_channels, iter_catalog_entries, sync_region
from health.stream_probe import probe_stream_url


SAMPLE_PAYLOAD = {
    "date": "2026-06-09 08:00:00",
    "channels": {
        "Sports": [
            {
                "name": "Test Sports HD",
                "logo": "https://example.com/logo.png",
                "group": "Sports",
                "source": "https://example.com/source.m3u",
                "url": "https://example.com/stream.m3u8",
            },
            {
                "name": "Dead Stream",
                "group": "Sports",
                "url": "https://example.com/dead.m3u8",
            },
        ]
    },
}


class CatalogSyncTests(TestCase):
    def test_make_external_key_stable(self):
        key1 = make_external_key("Bangladesh", "Channel A", "https://a.m3u8")
        key2 = make_external_key("Bangladesh", "Channel A", "https://a.m3u8")
        self.assertEqual(key1, key2)

    def test_make_group_key_case_insensitive(self):
        self.assertEqual(make_group_key("Channel A"), make_group_key("channel a"))

    def test_make_group_key_ignores_region_and_category(self):
        key1 = make_group_key("Channel A")
        key2 = make_group_key("Channel B")
        self.assertNotEqual(key1, key2)

    def test_iter_catalog_entries(self):
        entries = list(iter_catalog_entries(SAMPLE_PAYLOAD, "Bangladesh"))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["name"], "Test Sports HD")

    def test_iter_catalog_entries_truncates_display_text_not_urls(self):
        long_name = "N" * 600
        long_url = "https://example.com/" + ("a" * 2100) + ".m3u8"
        long_logo = "https://example.com/" + ("l" * 1100) + ".png"
        payload = {
            "date": "2026-06-09",
            "channels": {
                "Sports": [
                    {
                        "name": long_name,
                        "url": long_url,
                        "group": "G" * 300,
                        "logo": long_logo,
                    }
                ]
            },
        }
        entries = list(iter_catalog_entries(payload, "Bangladesh"))
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(len(entry["name"]), 512)
        self.assertEqual(len(entry["category"]), 255)
        self.assertEqual(entry["stream_url"], long_url)
        self.assertEqual(entry["logo_url"], long_logo)
        self.assertIn("_truncated_fields", entry)
        self.assertNotIn("stream_url", entry["_truncated_fields"])
        self.assertNotIn("logo_url", entry["_truncated_fields"])

    def test_fit_catalog_entry_preserves_external_key_inputs(self):
        long_name = "A" * 600
        stream_url = "https://example.com/live.m3u8"
        entry, truncated = fit_catalog_entry(
            {
                "external_key": make_external_key("Bangladesh", long_name, stream_url),
                "group_key": make_group_key(long_name),
                "region": "Bangladesh",
                "category": "Sports",
                "name": long_name,
                "logo_url": "",
                "stream_url": stream_url,
                "source_url": "",
                "source_date": "2026-06-09",
            }
        )
        self.assertEqual(truncated, ["name"])
        self.assertEqual(len(entry["name"]), 512)
        self.assertEqual(
            entry["external_key"],
            make_external_key("Bangladesh", long_name, stream_url),
        )

    @patch("catalog.sync.fetch_region_payload")
    def test_sync_region_truncates_long_name(self, mock_fetch):
        long_name = "Channel " + ("X" * 600)
        mock_fetch.return_value = {
            "date": "2026-06-09",
            "channels": {
                "Sports": [
                    {"name": long_name, "url": "https://example.com/live.m3u8"},
                ]
            },
        }
        result = sync_region("Bangladesh", verify_streams=False)
        self.assertEqual(result.created, 1)
        self.assertEqual(result.truncated, 1)
        channel = CatalogChannel.objects.get()
        self.assertEqual(len(channel.name), 512)

    @patch("catalog.sync.fetch_region_payload")
    def test_sync_region_preserves_long_stream_url(self, mock_fetch):
        long_url = "https://example.com/" + ("x" * 3000) + "/live.m3u8"
        mock_fetch.return_value = {
            "date": "2026-06-09",
            "channels": {
                "Sports": [
                    {"name": "Long URL Channel", "url": long_url},
                ]
            },
        }
        result = sync_region("Bangladesh", verify_streams=False)
        self.assertEqual(result.created, 1)
        channel = CatalogChannel.objects.get()
        self.assertEqual(channel.stream_url, long_url)

    def test_is_hls_stream_url(self):
        self.assertTrue(is_hls_stream_url("https://cdn.example.com/live/playlist.m3u8"))
        self.assertTrue(is_hls_stream_url("https://cdn.example.com/stream?fmt=m3u8"))
        self.assertFalse(is_hls_stream_url("https://cdn.example.com/video.mp4"))
        self.assertFalse(is_hls_stream_url(""))

    def test_iter_catalog_entries_skips_mp4(self):
        payload = {
            "date": "2026-06-09",
            "channels": {
                "Sports": [
                    {"name": "MP4 Channel", "url": "https://example.com/live.mp4"},
                    {"name": "HLS Channel", "url": "https://example.com/live.m3u8"},
                ]
            },
        }
        entries = list(iter_catalog_entries(payload, "Bangladesh"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "HLS Channel")

    @patch("catalog.sync.fetch_region_payload")
    def test_sync_deactivates_existing_mp4_channels(self, mock_fetch):
        CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "Old MP4", "https://example.com/old.mp4"),
            region="Bangladesh",
            category="News",
            name="Old MP4",
            stream_url="https://example.com/old.mp4",
            is_active=True,
        )
        mock_fetch.return_value = {"date": "2026-06-09", "channels": {}}
        result = sync_region("Bangladesh", deactivate_missing=True, verify_streams=False)
        self.assertGreaterEqual(result.deactivated, 1)
        channel = CatalogChannel.objects.get(name="Old MP4")
        self.assertFalse(channel.is_active)
        self.assertEqual(channel.deactivation_reason, DeactivationReason.UNSUPPORTED_FORMAT)

    def test_deactivate_non_hls_channels(self):
        CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "MP4", "https://example.com/a.mp4"),
            region="Bangladesh",
            category="Sports",
            name="MP4",
            stream_url="https://example.com/a.mp4",
        )
        CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "HLS", "https://example.com/a.m3u8"),
            region="Bangladesh",
            category="Sports",
            name="HLS",
            stream_url="https://example.com/a.m3u8",
        )
        count = deactivate_non_hls_channels("Bangladesh")
        self.assertEqual(count, 1)
        self.assertFalse(CatalogChannel.objects.get(name="MP4").is_active)
        self.assertTrue(CatalogChannel.objects.get(name="HLS").is_active)

    @patch("catalog.sync.fetch_region_payload")
    def test_sync_region_creates_and_updates(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_PAYLOAD
        result = sync_region("Bangladesh", deactivate_missing=True, verify_streams=False)
        self.assertEqual(result.created, 2)
        self.assertEqual(CatalogChannel.objects.count(), 2)

        mock_fetch.return_value = SAMPLE_PAYLOAD
        result2 = sync_region("Bangladesh", deactivate_missing=True, verify_streams=False)
        self.assertEqual(result2.updated, 2)
        self.assertEqual(result2.created, 0)

    @patch("catalog.sync.fetch_region_payload")
    def test_sync_deactivates_missing_channels(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_PAYLOAD
        sync_region("Bangladesh", verify_streams=False)

        mock_fetch.return_value = {"date": "2026-06-09", "channels": {}}
        result = sync_region("Bangladesh", deactivate_missing=True, verify_streams=False)
        self.assertEqual(result.deactivated, 2)
        self.assertFalse(CatalogChannel.objects.filter(is_active=True).exists())

    @patch("catalog.sync.fetch_region_payload")
    def test_sync_does_not_reactivate_inactive_channels(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_PAYLOAD
        sync_region("Bangladesh", verify_streams=False)

        channel = CatalogChannel.objects.get(name="Test Sports HD")
        channel.is_active = False
        channel.deactivation_reason = "user_reports"
        channel.save()

        sync_region("Bangladesh", verify_streams=False)
        channel.refresh_from_db()
        self.assertFalse(channel.is_active)
        self.assertEqual(channel.deactivation_reason, "user_reports")

    @patch("catalog.probe.probe_stream_url")
    @patch("catalog.sync.fetch_region_payload")
    def test_sync_skips_unreachable_streams(self, mock_fetch, mock_probe):
        mock_fetch.return_value = SAMPLE_PAYLOAD

        def probe_side_effect(url, timeout=5):
            return url.endswith("stream.m3u8")

        mock_probe.side_effect = probe_side_effect

        result = sync_region("Bangladesh", verify_streams=True)
        self.assertEqual(result.created, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(CatalogChannel.objects.count(), 1)
        self.assertEqual(CatalogChannel.objects.get().name, "Test Sports HD")


class CatalogChannelAdminTests(TestCase):
    def setUp(self):
        self.channel = CatalogChannel.objects.create(
            external_key="bd-test",
            name="Test Sports HD",
            region="Bangladesh",
            category="Sports",
            stream_url="https://example.com/stream.m3u8",
            is_active=True,
        )
        self.admin = CatalogChannelAdmin(CatalogChannel, AdminSite())
        self.request = RequestFactory().get("/admin/")
        self.request.user = MagicMock(is_active=True, is_staff=True)
        self.request.session = "session"
        setattr(self.request, "_messages", FallbackStorage(self.request))

    def test_mark_dead_link_deactivates_channel(self):
        queryset = CatalogChannel.objects.filter(pk=self.channel.pk)
        self.admin.mark_dead_link(self.request, queryset)
        self.channel.refresh_from_db()
        self.assertFalse(self.channel.is_active)
        self.assertEqual(self.channel.deactivation_reason, DeactivationReason.DEAD_LINK)
        self.assertIsNotNone(self.channel.deactivated_at)

    @patch("catalog.admin_actions.probe_stream_url", return_value=False)
    def test_probe_and_deactivate_if_dead(self, _mock_probe):
        queryset = CatalogChannel.objects.filter(pk=self.channel.pk)
        self.admin.probe_and_deactivate_if_dead(self.request, queryset)
        self.channel.refresh_from_db()
        self.assertFalse(self.channel.is_active)
        self.assertEqual(self.channel.deactivation_reason, DeactivationReason.DEAD_LINK)

    @patch("catalog.admin_actions.probe_stream_url", return_value=True)
    def test_probe_keeps_live_channel_active(self, _mock_probe):
        queryset = CatalogChannel.objects.filter(pk=self.channel.pk)
        self.admin.probe_and_deactivate_if_dead(self.request, queryset)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.is_active)


class StreamProbeTests(TestCase):
    @patch("health.stream_probe.requests.head")
    def test_probe_accepts_ok_head(self, mock_head):
        mock_head.return_value.status_code = 200
        self.assertTrue(probe_stream_url("https://example.com/live.m3u8"))

    @patch("health.stream_probe.requests.get")
    @patch("health.stream_probe.requests.head")
    def test_probe_falls_back_to_get(self, mock_head, mock_get):
        mock_head.return_value.status_code = 405
        mock_get.return_value.status_code = 200
        mock_get.return_value.close = lambda: None
        self.assertTrue(probe_stream_url("https://example.com/live.m3u8"))

    def test_filter_reachable_entries(self):
        entries = [
            {"name": "A", "stream_url": "https://example.com/a.m3u8"},
            {"name": "B", "stream_url": "https://example.com/b.m3u8"},
        ]
        with patch("catalog.probe.probe_stream_url") as mock_probe:
            mock_probe.side_effect = lambda url, timeout=5: url.endswith("a.m3u8")
            alive, skipped = filter_reachable_entries(entries, workers=2)
        self.assertEqual(len(alive), 1)
        self.assertEqual(skipped, 1)
        self.assertEqual(alive[0]["name"], "A")
