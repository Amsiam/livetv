from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from catalog.deactivation import DeactivationReason
from catalog.models import CatalogChannel
from health.chunking import chunk_list
from health.stream_health import (
    probe_active_streams,
    probe_match_channel_ids,
    probe_tv_channel_ids,
    reactivate_recovered_streams,
)
from matches.models import Channel, Match, MatchStatus


class ChunkingTests(TestCase):
    def test_chunk_list_splits_evenly(self):
        self.assertEqual(chunk_list([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])

    def test_chunk_list_empty(self):
        self.assertEqual(chunk_list([], 100), [])


class StreamHealthTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.match = Match.objects.create(
            title="Test",
            sport="football",
            home_team="A",
            away_team="B",
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            status=MatchStatus.LIVE,
        )
        self.match_channel = Channel.objects.create(
            match=self.match,
            name="Match HD",
            stream_url="https://example.com/match.m3u8",
            is_active=True,
        )
        self.tv_channel = CatalogChannel.objects.create(
            external_key="tv-1",
            name="TV HD",
            region="Bangladesh",
            category="News",
            stream_url="https://example.com/tv.m3u8",
            is_active=True,
        )

    @patch("health.stream_health.probe_stream_url", return_value=False)
    def test_probe_tv_channel_ids_batch(self, _mock_probe):
        stats = probe_tv_channel_ids([str(self.tv_channel.id)], timeout=1)
        self.assertEqual(stats.checked, 1)
        self.assertEqual(stats.failures, 1)

    @patch("health.stream_health.probe_stream_url", return_value=False)
    def test_probe_match_channel_ids_batch(self, _mock_probe):
        stats = probe_match_channel_ids([str(self.match_channel.id)], timeout=1)
        self.assertEqual(stats.checked, 1)
        self.assertEqual(stats.failures, 1)

    @override_settings(
        CHANNEL_FAILURE_THRESHOLD=10,
        CHANNEL_HEALTH_FAILURE_THRESHOLD=3,
    )
    @patch("health.stream_health.probe_stream_url", return_value=False)
    def test_health_probe_deactivates_before_client_threshold(self, _mock_probe):
        probe_tv_channel_ids([str(self.tv_channel.id)], timeout=1)
        probe_tv_channel_ids([str(self.tv_channel.id)], timeout=1)
        self.assertTrue(self.tv_channel.is_active)

        stats = probe_tv_channel_ids([str(self.tv_channel.id)], timeout=1)
        self.tv_channel.refresh_from_db()
        self.assertEqual(stats.deactivated, 1)
        self.assertFalse(self.tv_channel.is_active)
        self.assertEqual(self.tv_channel.deactivation_reason, DeactivationReason.HEALTH_CHECK)

    @override_settings(
        CHANNEL_FAILURE_THRESHOLD=2,
        CHANNEL_HEALTH_FAILURE_THRESHOLD=2,
    )
    @patch("health.stream_health.probe_stream_url", return_value=False)
    def test_probe_deactivates_after_threshold(self, _mock_probe):
        result = probe_active_streams(timeout=1)
        self.assertEqual(result.match_channels.checked, 1)
        self.assertEqual(result.tv_channels.checked, 1)

        probe_active_streams(timeout=1)
        self.match_channel.refresh_from_db()
        self.tv_channel.refresh_from_db()
        self.assertFalse(self.match_channel.is_active)
        self.assertFalse(self.tv_channel.is_active)
        self.assertEqual(self.tv_channel.deactivation_reason, DeactivationReason.HEALTH_CHECK)

    @override_settings(CHANNEL_HEALTH_FAILURE_THRESHOLD=3)
    @patch("health.stream_health.probe_stream_url", return_value=True)
    def test_reactivate_recovered_streams(self, _mock_probe):
        self.tv_channel.is_active = False
        self.tv_channel.deactivation_reason = DeactivationReason.HEALTH_CHECK
        self.tv_channel.failure_count = 1
        self.tv_channel.save()

        result = reactivate_recovered_streams(timeout=1)
        self.tv_channel.refresh_from_db()
        self.assertEqual(result.tv_channels.reactivated, 1)
        self.assertTrue(self.tv_channel.is_active)
        self.assertEqual(self.tv_channel.deactivation_reason, "")

    @override_settings(CHANNEL_FAILURE_THRESHOLD=100)
    @patch("health.stream_health.probe_stream_url", return_value=False)
    def test_confirmed_dead_inactive_channels_skip_reactivation_probe(self, mock_probe):
        self.tv_channel.is_active = False
        self.tv_channel.deactivation_reason = DeactivationReason.USER_REPORTS
        self.tv_channel.failure_count = 100
        self.tv_channel.save()

        result = reactivate_recovered_streams(timeout=1)
        self.assertEqual(result.tv_channels.checked, 0)
        mock_probe.assert_not_called()

    @override_settings(
        CHANNEL_FAILURE_THRESHOLD=100,
        CHANNEL_HEALTH_FAILURE_THRESHOLD=3,
    )
    @patch("health.stream_health.probe_stream_url", return_value=True)
    def test_health_deactivated_below_client_threshold_still_reactivates(self, _mock_probe):
        self.tv_channel.is_active = False
        self.tv_channel.deactivation_reason = DeactivationReason.HEALTH_CHECK
        self.tv_channel.failure_count = 3
        self.tv_channel.save()

        result = reactivate_recovered_streams(timeout=1)
        self.tv_channel.refresh_from_db()
        self.assertEqual(result.tv_channels.reactivated, 1)
        self.assertTrue(self.tv_channel.is_active)

    @patch("health.stream_health.probe_stream_url", return_value=True)
    def test_dead_link_channels_skip_reactivation_probe(self, mock_probe):
        self.tv_channel.is_active = False
        self.tv_channel.deactivation_reason = DeactivationReason.DEAD_LINK
        self.tv_channel.failure_count = 0
        self.tv_channel.save()

        result = reactivate_recovered_streams(timeout=1)
        self.assertEqual(result.tv_channels.checked, 0)
        mock_probe.assert_not_called()

    @patch("health.stream_health.probe_stream_url", return_value=True)
    def test_admin_deactivated_channels_are_not_auto_reactivated(self, _mock_probe):
        self.tv_channel.is_active = False
        self.tv_channel.deactivation_reason = DeactivationReason.ADMIN
        self.tv_channel.save()

        result = reactivate_recovered_streams(timeout=1)
        self.tv_channel.refresh_from_db()
        self.assertEqual(result.tv_channels.reactivated, 0)
        self.assertFalse(self.tv_channel.is_active)


SAMPLE_PAYLOAD = {
    "date": "2026-06-09 08:00:00",
    "channels": {
        "Sports": [
            {
                "name": "Chunk Test HD",
                "group": "Sports",
                "url": "https://example.com/stream.m3u8",
            },
        ]
    },
}


class CeleryTaskTests(TestCase):
    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CATALOG_SYNC_CHUNK_SIZE=1,
        LIVETV_COLLECTOR_REGIONS="Bangladesh",
    )
    @patch("catalog.sync.fetch_region_payload", return_value=SAMPLE_PAYLOAD)
    def test_sync_tv_catalog_task_eager(self, _mock_fetch):
        from catalog.models import CatalogSyncRun
        from health.tasks import sync_tv_catalog_task

        result = sync_tv_catalog_task()
        self.assertEqual(result["status"], "dispatched")
        self.assertTrue(CatalogChannel.objects.filter(name="Chunk Test HD").exists())
        run = CatalogSyncRun.objects.get(pk=result["sync_run_id"])
        self.assertIsNotNone(run.finished_at)

    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        LIVETV_COLLECTOR_REGIONS="Bangladesh",
    )
    @patch("catalog.sync.fetch_region_payload", return_value=SAMPLE_PAYLOAD)
    def test_sync_tv_catalog_skips_when_lock_held(self, _mock_fetch):
        from django.core.cache import cache

        from catalog.models import CatalogSyncRun
        from health.tasks import SYNC_CATALOG_LOCK_KEY, sync_tv_catalog_task

        cache.add(SYNC_CATALOG_LOCK_KEY, "1", timeout=60)
        before = CatalogSyncRun.objects.count()
        result = sync_tv_catalog_task()
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(CatalogSyncRun.objects.count(), before)
        cache.delete(SYNC_CATALOG_LOCK_KEY)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, STREAM_PROBE_WORKERS=4)
    @patch("health.stream_health.probe_stream_url")
    def test_probe_tv_channels_parallel(self, mock_probe):
        channels = [
            CatalogChannel.objects.create(
                external_key=f"parallel-{index}",
                name=f"Parallel {index}",
                region="Bangladesh",
                category="News",
                stream_url=f"https://example.com/{index}.m3u8",
                is_active=True,
            )
            for index in range(4)
        ]
        stats = probe_tv_channel_ids(
            [str(channel.id) for channel in channels],
            timeout=1,
            workers=4,
        )
        self.assertEqual(stats.checked, 4)
        self.assertEqual(mock_probe.call_count, 4)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, STREAM_PROBE_CHUNK_SIZE=50)
    @patch("health.stream_health.probe_stream_url", return_value=True)
    def test_probe_active_streams_dispatches_chunks(self, _mock_probe):
        CatalogChannel.objects.create(
            external_key="probe-chunk",
            name="Probe Chunk",
            region="Bangladesh",
            category="News",
            stream_url="https://example.com/tv.m3u8",
            is_active=True,
        )
        from health.tasks import probe_active_streams_task

        result = probe_active_streams_task()
        self.assertEqual(result["status"], "dispatched")
        self.assertGreaterEqual(result["chunks"], 1)
