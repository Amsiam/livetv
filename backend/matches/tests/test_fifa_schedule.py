from catalog.models import CatalogChannel, make_external_key
from django.test import TestCase

from matches.data.fifa_world_cup_2026_schedule import (
    FIFA_WORLD_CUP_2026_CATEGORY,
    FIFA_WORLD_CUP_2026_SPORT,
    SCHEDULE,
)
from matches.fifa_schedule import (
    build_match_title,
    import_fifa_world_cup_2026_schedule,
    resolve_fifa_channels,
)
from matches.models import Channel, Match


class FifaScheduleImportTests(TestCase):
    def setUp(self):
        CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "T Sports HD", "https://cdn.example/0.m3u8"
            ),
            region="Bangladesh",
            category="Sports",
            name="T Sports HD",
            stream_url="https://cdn.example/0.m3u8",
        )
        CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh",
                "T Sports HD 🇧🇩",
                "https://cdn.example/1.m3u8",
            ),
            region="Bangladesh",
            category=FIFA_WORLD_CUP_2026_CATEGORY,
            name="T Sports HD 🇧🇩",
            stream_url="https://cdn.example/1.m3u8",
        )
        CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh",
                "Somoy FIFA",
                "https://cdn.example/2.m3u8",
            ),
            region="Bangladesh",
            category=FIFA_WORLD_CUP_2026_CATEGORY,
            name="Somoy 🇧🇩 FIFA World Cup 2026",
            stream_url="https://cdn.example/2.m3u8",
        )

    def test_resolve_includes_category_and_preferred(self):
        resolved = resolve_fifa_channels()
        labels = [label for label, _, _ in resolved]
        self.assertEqual(labels[0], "T Sports HD")
        self.assertEqual(labels[1], "T Sports HD 🇧🇩")
        self.assertIn("Somoy 🇧🇩 FIFA World Cup 2026", labels)

    def test_build_match_title_group_stage(self):
        title = build_match_title(SCHEDULE[0])
        self.assertEqual(title, "M1 · Group A: Mexico vs South Africa")

    def test_build_match_title_knockout(self):
        final = SCHEDULE[-1]
        title = build_match_title(final)
        self.assertEqual(title, "M104 · Final: W101 vs W102")

    def test_import_creates_all_matches_with_channels(self):
        result = import_fifa_world_cup_2026_schedule()
        self.assertEqual(result["matches_created"], 104)
        self.assertEqual(result["total_matches"], 104)
        self.assertEqual(len(result["tv_channels"]), 3)
        self.assertEqual(
            Match.objects.filter(sport=FIFA_WORLD_CUP_2026_SPORT).count(),
            104,
        )
        self.assertEqual(
            Channel.objects.filter(match__sport=FIFA_WORLD_CUP_2026_SPORT).count(),
            312,
        )
        match = Match.objects.get(
            sport=FIFA_WORLD_CUP_2026_SPORT,
            match_number=1,
        )
        channel_names = set(match.channels.values_list("name", flat=True))
        self.assertEqual(
            channel_names,
            {"T Sports HD", "T Sports HD 🇧🇩", "Somoy 🇧🇩 FIFA World Cup 2026"},
        )
        bd = match.channels.get(name="T Sports HD 🇧🇩")
        self.assertEqual(bd.catalog_channel.category, FIFA_WORLD_CUP_2026_CATEGORY)

    def test_import_is_idempotent(self):
        import_fifa_world_cup_2026_schedule()
        result = import_fifa_world_cup_2026_schedule()
        self.assertEqual(result["matches_created"], 0)
        self.assertEqual(result["matches_updated"], 104)

    def test_reimport_replaces_stale_catalog_links(self):
        import_fifa_world_cup_2026_schedule(replace=True)
        match = Match.objects.get(sport=FIFA_WORLD_CUP_2026_SPORT, match_number=1)
        stale = CatalogChannel.objects.create(
            external_key=make_external_key(
                "Bangladesh", "Stale", "https://cdn.example/stale.m3u8"
            ),
            region="Bangladesh",
            category="Sports",
            name="Stale Sports HD",
            stream_url="https://cdn.example/stale.m3u8",
        )
        Channel.objects.create(
            match=match,
            catalog_channel=stale,
            name="Stale Sports HD",
            stream_url=stale.stream_url,
        )
        result = import_fifa_world_cup_2026_schedule()
        self.assertGreaterEqual(result["channels_removed"], 1)
        self.assertFalse(match.channels.filter(catalog_channel=stale).exists())
