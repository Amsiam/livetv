from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from catalog.models import CatalogChannel, make_external_key, make_group_key
from catalog.sync import propagate_linked_match_channels
from matches.models import Channel, Match, MatchStatus


class ChannelCatalogLinkTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.match = Match.objects.create(
            sport="football",
            home_team="A",
            away_team="B",
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            status=MatchStatus.LIVE,
        )
        self.catalog = CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "Sports HD", "https://cdn.example/a.m3u8"),
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/a.m3u8",
        )

    def test_catalog_only_fills_fields_on_save(self):
        channel = Channel(match=self.match, catalog_channel=self.catalog)
        channel.full_clean()
        channel.save()

        self.assertEqual(channel.name, "Sports HD")
        self.assertEqual(channel.stream_url, "https://cdn.example/a.m3u8")
        self.assertTrue(channel.follow_catalog_stream)

    def test_manual_stream_without_catalog(self):
        channel = Channel.objects.create(
            match=self.match,
            name="Custom",
            stream_url="https://manual.example/stream.m3u8",
        )
        self.assertFalse(channel.follow_catalog_stream)

    def test_custom_url_overrides_catalog_sync(self):
        channel = Channel.objects.create(
            match=self.match,
            catalog_channel=self.catalog,
            name="Sports HD",
            stream_url="https://manual.example/override.m3u8",
        )
        self.assertFalse(channel.follow_catalog_stream)

        self.catalog.stream_url = "https://cdn.example/new.m3u8"
        self.catalog.save()
        propagate_linked_match_channels(CatalogChannel.objects.filter(pk=self.catalog.pk))

        channel.refresh_from_db()
        self.assertEqual(channel.stream_url, "https://manual.example/override.m3u8")

    def test_catalog_link_normalizes_to_primary_in_group(self):
        group_key = make_group_key("Sports HD")
        self.catalog.group_key = group_key
        self.catalog.save(update_fields=["group_key"])
        alternate = CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Sports HD", "https://cdn.example/alt.m3u8"
            ),
            group_key=group_key,
            region="Bangladesh",
            category="Sports",
            name="Sports HD",
            stream_url="https://cdn.example/alt.m3u8",
            failure_count=0,
        )
        self.catalog.failure_count = 5
        self.catalog.save(update_fields=["failure_count"])

        channel = Channel.objects.create(
            match=self.match,
            catalog_channel=alternate,
            name="",
            stream_url="",
        )

        self.assertEqual(channel.catalog_channel_id, alternate.id)
        self.assertEqual(channel.name, "Sports HD")
        self.assertEqual(channel.stream_url, alternate.stream_url)

    def test_linked_channel_follows_catalog_sync(self):
        channel = Channel.objects.create(
            match=self.match,
            catalog_channel=self.catalog,
            name="Sports HD",
            stream_url="https://cdn.example/a.m3u8",
        )

        self.catalog.stream_url = "https://cdn.example/new.m3u8"
        self.catalog.save()
        propagate_linked_match_channels(CatalogChannel.objects.filter(pk=self.catalog.pk))

        channel.refresh_from_db()
        self.assertEqual(channel.stream_url, "https://cdn.example/new.m3u8")
