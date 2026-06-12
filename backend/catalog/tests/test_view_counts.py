from unittest.mock import patch

from django.test import TestCase, override_settings

from catalog.models import CatalogChannel, make_external_key
from catalog.view_counts import (
    batch_effective_view_counts,
    flush_pending_view_counts_to_db,
    record_channel_view,
)


class ViewCountRedisTests(TestCase):
    def setUp(self):
        self.channel = CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Popular TV", "https://cdn.example/a.m3u8"
            ),
            region="Bangladesh",
            category="News",
            name="Popular TV",
            stream_url="https://cdn.example/a.m3u8",
            view_count=10,
        )

    @override_settings(REDIS_URL="")
    def test_record_view_falls_back_to_db_without_redis(self):
        count, recorded = record_channel_view(self.channel.id, db_count=10)
        self.channel.refresh_from_db()
        self.assertTrue(recorded)
        self.assertEqual(count, 11)
        self.assertEqual(self.channel.view_count, 11)

    @override_settings(REDIS_URL="redis://localhost:6379/15")
    def test_record_view_uses_redis_without_db_write(self):
        from django_redis import get_redis_connection

        client = get_redis_connection("default")
        client.delete("tv:channel_views:pending", "tv:channel_views:rank")

        count, recorded = record_channel_view(self.channel.id, db_count=10)
        self.channel.refresh_from_db()

        self.assertTrue(recorded)
        self.assertEqual(count, 11)
        self.assertEqual(self.channel.view_count, 10)

        effective = batch_effective_view_counts({str(self.channel.id): 10})
        self.assertEqual(effective[str(self.channel.id)], 11)

        result = flush_pending_view_counts_to_db()
        self.channel.refresh_from_db()
        self.assertEqual(result["flushed"], 1)
        self.assertEqual(self.channel.view_count, 11)

        client.delete("tv:channel_views:pending", "tv:channel_views:rank")

    @override_settings(REDIS_URL="redis://localhost:6379/15")
    @patch("catalog.view_counts._redis_client", return_value=None)
    def test_flush_skips_when_redis_unavailable(self, _mock_redis):
        result = flush_pending_view_counts_to_db()
        self.assertEqual(result["status"], "skipped")
