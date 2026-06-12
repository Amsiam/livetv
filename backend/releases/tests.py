from django.core.cache import cache
from django.test import TestCase, override_settings

from releases.cache import latest_release_cache_key
from releases.models import AppRelease
from releases.services import evaluate_app_update


class AppUpdateTests(TestCase):
    def setUp(self):
        AppRelease.objects.create(
            platform="android",
            version_name="1.0.1",
            build_number=5,
            min_build_number=3,
            download_url="https://cdn.example.com/livetv-1.0.1.apk",
            force_update=False,
            release_notes="Bug fixes",
        )

    def test_no_update_when_current(self):
        result = evaluate_app_update(platform="android", current_build=5)
        self.assertFalse(result["update_available"])
        self.assertFalse(result["force_update"])

    def test_optional_update(self):
        result = evaluate_app_update(platform="android", current_build=4)
        self.assertTrue(result["update_available"])
        self.assertFalse(result["force_update"])
        self.assertEqual(result["version_name"], "1.0.1")

    def test_force_below_minimum(self):
        result = evaluate_app_update(platform="android", current_build=2)
        self.assertTrue(result["update_available"])
        self.assertTrue(result["force_update"])

    def test_force_flag(self):
        AppRelease.objects.filter(build_number=5).update(force_update=True)
        result = evaluate_app_update(platform="android", current_build=4)
        self.assertTrue(result["force_update"])

    def test_api_endpoint(self):
        response = self.client.get("/v1/app-update/", {"platform": "android", "build": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["update_available"])
        self.assertTrue(data["force_update"])
        self.assertIn("livetv-1.0.1.apk", data["download_url"])

    @override_settings(PUBLIC_API_URL="", DEBUG=True)
    def test_api_returns_stored_download_url(self):
        release = AppRelease.objects.get(build_number=5)
        release.download_url = "https://tunnel.example.com/media/releases/foo.apk"
        release.save(update_fields=["download_url", "updated_at"])
        cache.clear()

        response = self.client.get("/v1/app-update/", {"platform": "android", "build": 1})
        self.assertEqual(
            response.json()["download_url"],
            "https://tunnel.example.com/media/releases/foo.apk",
        )

    @override_settings(APP_UPDATE_CACHE_TTL=300)
    def test_api_cache_headers(self):
        response = self.client.get("/v1/app-update/", {"platform": "android", "build": 1})
        self.assertEqual(response["Cache-Control"], "public, max-age=300, s-maxage=300")
        self.assertEqual(response["CDN-Cache-Control"], "max-age=300")

    @override_settings(APP_UPDATE_CACHE_TTL=300)
    def test_latest_release_cached_until_admin_change(self):
        cache.clear()
        with self.assertNumQueries(1):
            self.client.get("/v1/app-update/", {"platform": "android", "build": 1})
        with self.assertNumQueries(0):
            self.client.get("/v1/app-update/", {"platform": "android", "build": 4})

        release = AppRelease.objects.get(build_number=5)
        release.version_name = "1.0.2"
        release.save()
        self.assertIsNone(cache.get(latest_release_cache_key("android")))
        with self.assertNumQueries(1):
            response = self.client.get("/v1/app-update/", {"platform": "android", "build": 4})
        self.assertEqual(response.json()["version_name"], "1.0.2")
