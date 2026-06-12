from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from catalog.models import CatalogChannel, make_external_key, make_group_key
from matches.models import Channel, Match, MatchStatus


class MatchApiTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.match = Match.objects.create(
            sport="football",
            home_team="Team A",
            away_team="Team B",
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            status=MatchStatus.LIVE,
        )
        Channel.objects.create(
            match=self.match,
            name="HD Stream",
            stream_url="https://example.com/stream.m3u8",
            priority=1,
        )
        Channel.objects.create(
            match=self.match,
            name="Backup",
            stream_url="https://example.com/backup.m3u8",
            priority=0,
            is_active=False,
        )

    def test_health(self):
        response = self.client.get("/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")

    @override_settings(MATCH_LIST_CACHE_TTL=60)
    def test_match_list_cache_control_headers(self):
        response = self.client.get("/v1/matches/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "public, max-age=60, s-maxage=60")
        self.assertEqual(response["CDN-Cache-Control"], "max-age=60")
        self.assertTrue(response["ETag"])

    def test_list_live_matches(self):
        response = self.client.get("/v1/matches/", {"status": "live"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_match_detail_returns_active_channels_only(self):
        response = self.client.get(f"/v1/matches/{self.match.id}/")
        self.assertEqual(response.status_code, 200)
        channels = response.json()["channels"]
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["name"], "HD Stream")

    def test_match_channels_endpoint(self):
        response = self.client.get(f"/v1/matches/{self.match.id}/channels/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_match_detail_includes_catalog_group_sources(self):
        group_key = make_group_key("Sports HD")
        catalog_primary = CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/a.m3u8"
            ),
            group_key=group_key,
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/a.m3u8",
        )
        CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/b.m3u8"
            ),
            group_key=group_key,
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/b.m3u8",
        )
        Channel.objects.create(
            match=self.match,
            catalog_channel=catalog_primary,
            name="Sports HD",
            stream_url="https://cdn.example/a.m3u8",
            priority=2,
        )

        response = self.client.get(f"/v1/matches/{self.match.id}/")
        self.assertEqual(response.status_code, 200)
        channels = response.json()["channels"]
        sports = [item for item in channels if item["name"] == "Sports HD"]
        self.assertEqual(len(sports), 1)
        self.assertEqual(sports[0]["source_count"], 2)
        self.assertEqual(len(sports[0]["sources"]), 2)
        kinds = {source["kind"] for source in sports[0]["sources"]}
        self.assertEqual(kinds, {"match", "catalog"})

    def test_match_detail_groups_same_name_sources(self):
        Channel.objects.create(
            match=self.match,
            name="hd stream",
            stream_url="https://example.com/stream-alt.m3u8",
            priority=0,
        )
        response = self.client.get(f"/v1/matches/{self.match.id}/")
        self.assertEqual(response.status_code, 200)
        channels = response.json()["channels"]
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["name"], "HD Stream")
        self.assertEqual(channels[0]["source_count"], 2)
        self.assertEqual(len(channels[0]["sources"]), 2)

    def test_match_hidden_before_visibility_window(self):
        future_start = timezone.now() + timedelta(days=2, hours=4)
        match = Match.objects.create(
            sport="football",
            home_team="Future",
            away_team="Teams",
            starts_at=future_start,
            ends_at=future_start + timedelta(hours=2),
            status=MatchStatus.SCHEDULED,
        )
        response = self.client.get("/v1/matches/")
        ids = [item["id"] for item in response.json()["results"]]
        self.assertNotIn(str(match.id), ids)

    def test_match_visible_within_2d_3h_before_start(self):
        soon_start = timezone.now() + timedelta(days=2, hours=2)
        match = Match.objects.create(
            sport="football",
            home_team="Soon",
            away_team="Teams",
            starts_at=soon_start,
            ends_at=soon_start + timedelta(hours=2),
            status=MatchStatus.SCHEDULED,
        )
        response = self.client.get("/v1/matches/")
        ids = [item["id"] for item in response.json()["results"]]
        self.assertIn(str(match.id), ids)

    def test_match_hidden_after_end_time(self):
        now = timezone.now()
        match = Match.objects.create(
            sport="football",
            home_team="Past",
            away_team="Teams",
            starts_at=now - timedelta(hours=4),
            ends_at=now - timedelta(minutes=1),
            status=MatchStatus.ENDED,
        )
        response = self.client.get(f"/v1/matches/{match.id}/")
        self.assertEqual(response.status_code, 404)


class TvChannelApiTests(TestCase):
    def setUp(self):
        self.active = CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "Sports HD", "https://cdn.example/a.m3u8"),
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            logo_url="https://cdn.example/logo.png",
            stream_url="https://cdn.example/a.m3u8",
        )
        CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "News", "https://cdn.example/b.m3u8"),
            region="Bangladesh",
            category="News",
            name="News 24",
            stream_url="https://cdn.example/b.m3u8",
            is_active=False,
        )
        CatalogChannel.objects.create(
            external_key=make_external_key("India", "Star", "https://cdn.example/c.m3u8"),
            region="India",
            category="Entertainment",
            name="Star Plus",
            stream_url="https://cdn.example/c.m3u8",
        )

    def test_list_active_tv_channels(self):
        response = self.client.get("/v1/tv-channels/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        names = {item["name"] for item in data["results"]}
        self.assertEqual(names, {"Sports HD", "Star Plus"})

    def test_tv_channel_detail(self):
        response = self.client.get(f"/v1/tv-channels/{self.active.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Sports HD")
        self.assertEqual(data["stream_url"], "https://cdn.example/a.m3u8")
        self.assertNotIn("source_url", data)

    def test_tv_channel_detail_inactive_not_found(self):
        inactive = CatalogChannel.objects.get(name="News 24")
        response = self.client.get(f"/v1/tv-channels/{inactive.id}/")
        self.assertEqual(response.status_code, 404)

    def test_list_orders_by_view_count(self):
        self.active.view_count = 50
        self.active.save(update_fields=["view_count"])
        star = CatalogChannel.objects.get(name="Star Plus")
        star.view_count = 200
        star.save(update_fields=["view_count"])

        response = self.client.get("/v1/tv-channels/", {"region": "Bangladesh"})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Sports HD")

        response = self.client.get("/v1/tv-channels/")
        names = [item["name"] for item in response.json()["results"]]
        self.assertEqual(names[0], "Star Plus")
        self.assertEqual(names[1], "Sports HD")

    def test_grouped_list_orders_by_group_view_count(self):
        group_key = make_group_key("Sports HD")
        self.active.group_key = group_key
        self.active.view_count = 10
        self.active.save(update_fields=["group_key", "view_count"])
        CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/a2.m3u8"
            ),
            group_key=group_key,
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/a2.m3u8",
            view_count=90,
        )
        star = CatalogChannel.objects.get(name="Star Plus")
        star.view_count = 50
        star.save(update_fields=["view_count"])

        response = self.client.get("/v1/tv-channels/", {"grouped": "true"})
        names = [item["name"] for item in response.json()["results"]]
        self.assertEqual(names[0], "Sports HD")
        self.assertEqual(names[1], "Star Plus")

    def test_record_view_increments_count(self):
        response = self.client.post(f"/v1/tv-channels/{self.active.id}/record-view/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["recorded"])
        self.assertEqual(data["view_count"], 1)

        response = self.client.post(f"/v1/tv-channels/{self.active.id}/record-view/")
        self.assertEqual(response.json()["view_count"], 1)
        self.assertFalse(response.json()["recorded"])

    def test_filter_by_region(self):
        response = self.client.get("/v1/tv-channels/", {"region": "India"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["name"], "Star Plus")

    def test_filter_by_category(self):
        response = self.client.get("/v1/tv-channels/", {"category": "Sports"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_search_by_name(self):
        response = self.client.get("/v1/tv-channels/", {"search": "star"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_regions_endpoint(self):
        response = self.client.get("/v1/tv-channels/regions/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        regions = {item["region"]: item["channel_count"] for item in data}
        self.assertEqual(regions["Bangladesh"], 1)
        self.assertEqual(regions["India"], 1)

    def test_regions_endpoint_counts_grouped_channels(self):
        group_key = make_group_key("Sports HD")
        CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/a2.m3u8"
            ),
            group_key=group_key,
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/a2.m3u8",
        )
        self.active.group_key = group_key
        self.active.save(update_fields=["group_key"])

        response = self.client.get("/v1/tv-channels/regions/")
        self.assertEqual(response.status_code, 200)
        regions = {item["region"]: item["channel_count"] for item in response.json()}
        self.assertEqual(regions["Bangladesh"], 1)

    @override_settings(MATCH_LIST_CACHE_TTL=60)
    def test_tv_channel_list_cache_headers(self):
        response = self.client.get("/v1/tv-channels/")
        self.assertEqual(response["Cache-Control"], "public, max-age=60, s-maxage=60")
        self.assertTrue(response["ETag"])

    def test_grouped_list_groups_same_name_case_insensitive(self):
        group_key = make_group_key("Sports HD")
        CatalogChannel.objects.create(
            external_key=make_external_key(
                "India", "sports hd", "https://cdn.example/in.m3u8"
            ),
            group_key=group_key,
            region="India",
            category="Entertainment",
            name="sports hd",
            stream_url="https://cdn.example/in.m3u8",
        )
        self.active.group_key = group_key
        self.active.save(update_fields=["group_key"])

        response = self.client.get("/v1/tv-channels/", {"grouped": "true"})
        self.assertEqual(response.status_code, 200)
        sports = [
            item for item in response.json()["results"] if item["name"].lower() == "sports hd"
        ]
        self.assertEqual(len(sports), 1)
        self.assertEqual(sports[0]["source_count"], 2)

    def test_grouped_list_dedupes_same_logical_channel(self):
        group_key = make_group_key("Sports HD")
        duplicate = CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/a2.m3u8"
            ),
            group_key=group_key,
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/a2.m3u8",
        )
        self.active.group_key = group_key
        self.active.save(update_fields=["group_key"])

        response = self.client.get("/v1/tv-channels/", {"grouped": "true"})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        sports = [item for item in results if item["name"] == "Sports HD"]
        self.assertEqual(len(sports), 1)
        self.assertEqual(sports[0]["source_count"], 2)
        self.assertEqual(len(sports[0]["sources"]), 2)

        duplicate.failure_count = 0
        duplicate.save(update_fields=["failure_count"])
        self.active.failure_count = 5
        self.active.save(update_fields=["failure_count"])

        response = self.client.get("/v1/tv-channels/", {"grouped": "true"})
        sports = [
            item
            for item in response.json()["results"]
            if item["name"] == "Sports HD"
        ]
        self.assertEqual(sports[0]["id"], str(duplicate.id))

    def test_detail_includes_alternate_sources(self):
        group_key = make_group_key("Sports HD")
        second = CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/alt.m3u8"
            ),
            group_key=group_key,
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/alt.m3u8",
        )
        self.active.group_key = group_key
        self.active.save(update_fields=["group_key"])

        response = self.client.get(f"/v1/tv-channels/{second.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["source_count"], 2)
        self.assertEqual(len(data["sources"]), 2)
        labels = {source["label"] for source in data["sources"]}
        self.assertEqual(labels, {"Source 1", "Source 2"})


@override_settings(CHANNEL_FAILURE_THRESHOLD=3)
class TvChannelFailureTests(TestCase):
    def setUp(self):
        self.tv_channel = CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "News", "https://cdn.example/news.m3u8"),
            region="Bangladesh",
            category="News",
            name="News 24",
            stream_url="https://cdn.example/news.m3u8",
        )

    def test_report_tv_channel_failure(self):
        url = f"/v1/tv-channels/{self.tv_channel.id}/report-failure/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["failure_count"], 1)

    def test_report_tv_channel_failure_deactivates(self):
        url = f"/v1/tv-channels/{self.tv_channel.id}/report-failure/"
        for i in range(3):
            response = self.client.post(url, HTTP_X_FORWARDED_FOR=f"10.0.0.{i}")
        self.assertTrue(response.json()["deactivated"])
        self.tv_channel.refresh_from_db()
        self.assertFalse(self.tv_channel.is_active)

    def test_inactive_tv_channel_hidden_from_api(self):
        self.tv_channel.is_active = False
        self.tv_channel.save()
        response = self.client.get(f"/v1/tv-channels/{self.tv_channel.id}/")
        self.assertEqual(response.status_code, 404)

    @override_settings(CHANNEL_FAILURE_THRESHOLD=10)
    def test_tv_channel_hidden_from_list_after_10_failures(self):
        url = f"/v1/tv-channels/{self.tv_channel.id}/report-failure/"
        for i in range(10):
            self.client.post(url, HTTP_X_FORWARDED_FOR=f"10.0.0.{i}")

        list_response = self.client.get("/v1/tv-channels/")
        ids = [item["id"] for item in list_response.json()["results"]]
        self.assertNotIn(str(self.tv_channel.id), ids)

        regions = self.client.get("/v1/tv-channels/regions/").json()
        self.assertEqual(regions, [])


@override_settings(CHANNEL_FAILURE_THRESHOLD=3)
class ChannelFailureTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.match = Match.objects.create(
            sport="football",
            home_team="Team A",
            away_team="Team B",
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            status=MatchStatus.LIVE,
        )
        self.channel = Channel.objects.create(
            match=self.match,
            name="HD Stream",
            stream_url="https://example.com/stream.m3u8",
            priority=1,
        )

    def test_record_failure_deactivates_at_threshold(self):
        self.assertFalse(self.channel.record_failure())
        self.assertTrue(self.channel.is_active)
        self.assertEqual(self.channel.failure_count, 1)

        self.channel.record_failure()
        deactivated = self.channel.record_failure()
        self.channel.refresh_from_db()

        self.assertTrue(deactivated)
        self.assertFalse(self.channel.is_active)
        self.assertEqual(self.channel.failure_count, 3)

    def test_record_success_resets_failure_count(self):
        self.channel.failure_count = 2
        self.channel.save(update_fields=["failure_count"])
        self.channel.record_success()
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.failure_count, 0)

    def test_report_failure_endpoint(self):
        url = f"/v1/channels/{self.channel.id}/report-failure/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["failure_count"], 1)
        self.assertTrue(data["is_active"])
        self.assertFalse(data["deactivated"])

    def test_report_failure_deactivates_channel(self):
        url = f"/v1/channels/{self.channel.id}/report-failure/"
        response = None
        for i in range(3):
            response = self.client.post(url, HTTP_X_FORWARDED_FOR=f"10.0.0.{i}")
            self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["deactivated"])
        self.assertFalse(response.json()["is_active"])

        detail = self.client.get(f"/v1/matches/{self.match.id}/")
        self.assertEqual(len(detail.json()["channels"]), 0)

    def test_report_failure_rate_limited(self):
        url = f"/v1/channels/{self.channel.id}/report-failure/"
        self.client.post(url)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 429)

    def test_report_failure_accepts_catalog_source_id(self):
        catalog = CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/alt.m3u8"
            ),
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/alt.m3u8",
        )
        url = f"/v1/channels/{catalog.id}/report-failure/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        catalog.refresh_from_db()
        self.assertEqual(catalog.failure_count, 1)

    @override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="12345")
    @patch("matches.notifications.requests.post")
    def test_telegram_notified_on_deactivation(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.status_code = 200

        for i in range(3):
            self.channel.record_failure(source="health_check")

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["chat_id"], "12345")
        self.assertIn("Channel deactivated", payload["text"])
        self.assertIn("HD Stream", payload["text"])
