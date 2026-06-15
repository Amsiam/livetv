from django.core.management import call_command
from django.test import TestCase

from catalog.models import CatalogChannel, make_external_key


class PurgeCatalogChannelsTests(TestCase):
    def setUp(self):
        CatalogChannel.objects.create(
            external_key=make_external_key("Bangladesh", "BD News", "https://example.com/bd.m3u8"),
            region="Bangladesh",
            name="BD News",
            stream_url="https://example.com/bd.m3u8",
        )
        CatalogChannel.objects.create(
            external_key=make_external_key("India", "IN News", "https://example.com/in.m3u8"),
            region="India",
            name="IN News",
            stream_url="https://example.com/in.m3u8",
        )
        CatalogChannel.objects.create(
            external_key=make_external_key("Bahrain", "BH News", "https://example.com/bh.m3u8"),
            region="Bahrain",
            name="BH News",
            stream_url="https://example.com/bh.m3u8",
        )

    def test_keep_only_default_regions(self):
        call_command("purge_catalog_channels", "--keep-only")
        regions = set(CatalogChannel.objects.values_list("region", flat=True))
        self.assertEqual(regions, {"Bangladesh", "India"})

    def test_delete_specific_regions(self):
        call_command("purge_catalog_channels", "--regions", "Bangladesh,India")
        regions = set(CatalogChannel.objects.values_list("region", flat=True))
        self.assertEqual(regions, {"Bahrain"})
