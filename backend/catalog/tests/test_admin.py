from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from catalog.admin import InactiveCatalogChannel, InactiveCatalogChannelAdmin
from catalog.deactivation import DeactivationReason
from catalog.models import CatalogChannel


class InactiveCatalogChannelAdminTests(TestCase):
    def setUp(self):
        self.active = CatalogChannel.objects.create(
            external_key="active-1",
            name="Active News",
            region="Bangladesh",
            category="News",
            stream_url="https://example.com/active.m3u8",
            is_active=True,
        )
        self.inactive = CatalogChannel.objects.create(
            external_key="inactive-1",
            name="Dead Sports",
            region="Bangladesh",
            category="Sports",
            stream_url="https://example.com/dead.m3u8",
            is_active=False,
            deactivation_reason=DeactivationReason.DEAD_LINK,
        )
        self.admin = InactiveCatalogChannelAdmin(InactiveCatalogChannel, AdminSite())
        self.request = RequestFactory().get("/admin/catalog/inactivecatalogchannel/")
        self.request.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="testpass123",
        )

    def test_inactive_queryset_excludes_active(self):
        qs = self.admin.get_queryset(self.request)
        names = list(qs.values_list("name", flat=True))
        self.assertIn("Dead Sports", names)
        self.assertNotIn("Active News", names)

    def test_search_does_not_force_active_only(self):
        qs = self.admin.get_queryset(self.request)
        results, _distinct = self.admin.get_search_results(
            self.request,
            qs,
            "Dead",
        )
        self.assertEqual(list(results), [self.inactive])
