import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from releases.models import AppRelease
from releases.pubspec import parse_pubspec_version


class PublishAppReleaseTests(TestCase):
    def test_parse_pubspec_version(self):
        pubspec = Path(__file__).resolve().parents[2] / "app" / "pubspec.yaml"
        version_name, build = parse_pubspec_version(pubspec)
        self.assertEqual(version_name, "1.0.6")
        self.assertEqual(build, 7)

    @override_settings(PUBLIC_API_URL="https://api.example.com")
    def test_publish_command_stores_apk_and_url(self):
        apk = Path(__file__).with_name("fixtures") / "sample.apk"
        apk.parent.mkdir(exist_ok=True)
        apk.write_bytes(b"PK fake apk")

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                try:
                    call_command(
                        "publish_app_release",
                        apk=str(apk),
                        version_name="9.9.9",
                        build_number=99,
                        notes="Test build",
                    )
                finally:
                    apk.unlink(missing_ok=True)

                release = AppRelease.objects.get(build_number=99)
                self.assertTrue(release.apk_file.name.startswith("releases/livetv-android"))
                self.assertEqual(
                    release.download_url,
                    "https://api.example.com/media/releases/livetv-android-v9.9.9-b99.apk",
                )
                self.assertEqual(release.release_notes, "Test build")

    @override_settings(PUBLIC_API_URL="https://api.example.com")
    def test_admin_form_upload_sets_url_on_first_save(self):
        apk_bytes = b"PK fake apk"
        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                user = get_user_model().objects.create_superuser(
                    "admin-upload",
                    "admin@example.com",
                    "secret",
                )
                client = Client()
                client.force_login(user)
                response = client.post(
                    reverse("admin:releases_apprelease_add"),
                    {
                        "platform": "android",
                        "version_name": "1.0.6",
                        "build_number": 7,
                        "min_build_number": 1,
                        "apk_file": SimpleUploadedFile(
                            "app-arm64-v8a-release.apk",
                            apk_bytes,
                            content_type="application/vnd.android.package-archive",
                        ),
                        "force_update": False,
                        "is_published": True,
                        "release_notes": "",
                    },
                    follow=True,
                )
                self.assertEqual(response.status_code, 200)

                release = AppRelease.objects.get(build_number=7)
                self.assertEqual(
                    release.apk_file.name,
                    "releases/livetv-android-v1.0.6-b7.apk",
                )
                self.assertEqual(
                    release.download_url,
                    "https://api.example.com/media/releases/livetv-android-v1.0.6-b7.apk",
                )
                change_page = client.get(
                    reverse("admin:releases_apprelease_change", args=[release.pk])
                )
                self.assertContains(
                    change_page,
                    "https://api.example.com/media/releases/livetv-android-v1.0.6-b7.apk",
                )

    @override_settings(PUBLIC_API_URL="https://api.example.com")
    def test_admin_change_reupload_clears_mangled_apk(self):
        from django.core.files.storage import default_storage

        apk_bytes = b"PK fake apk v1"
        canonical = "releases/livetv-android-v1.0.6-b7.apk"
        mangled = "releases/livetv-android-v1_KnM79xi.0.6-b7.apk"
        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                default_storage.save(mangled, SimpleUploadedFile("old.apk", apk_bytes))
                release = AppRelease.objects.create(
                    platform="android",
                    version_name="1.0.6",
                    build_number=7,
                    apk_file=mangled,
                    download_url="https://api.example.com/media/livetv-android-v1.0.6-b7.apk",
                )

                user = get_user_model().objects.create_superuser(
                    "admin-change",
                    "change@example.com",
                    "secret",
                )
                client = Client()
                client.force_login(user)
                response = client.post(
                    reverse("admin:releases_apprelease_change", args=[release.pk]),
                    {
                        "platform": "android",
                        "version_name": "1.0.6",
                        "build_number": 7,
                        "min_build_number": 1,
                        "apk_file": SimpleUploadedFile(
                            "app-arm64-v8a-release.apk",
                            b"PK fake apk v2",
                            content_type="application/vnd.android.package-archive",
                        ),
                        "force_update": False,
                        "is_published": True,
                        "release_notes": "",
                    },
                    follow=True,
                )
                self.assertEqual(response.status_code, 200)

                release.refresh_from_db()
                self.assertEqual(release.apk_file.name, canonical)
                self.assertEqual(
                    release.download_url,
                    "https://api.example.com/media/releases/livetv-android-v1.0.6-b7.apk",
                )
                change_page = client.get(
                    reverse("admin:releases_apprelease_change", args=[release.pk])
                )
                self.assertContains(
                    change_page,
                    "https://api.example.com/media/releases/livetv-android-v1.0.6-b7.apk",
                )

    @override_settings(PUBLIC_API_URL="https://api.example.com")
    def test_admin_upload_uses_canonical_download_url(self):
        apk_bytes = b"PK fake apk"
        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                release = AppRelease(
                    platform="android",
                    version_name="1.0.6",
                    build_number=7,
                )
                release.apk_file = SimpleUploadedFile(
                    "app-arm64-v8a-release.apk",
                    apk_bytes,
                    content_type="application/vnd.android.package-archive",
                )
                release.save()

                self.assertEqual(
                    release.apk_file.name,
                    "releases/livetv-android-v1.0.6-b7.apk",
                )
                self.assertEqual(
                    release.download_url,
                    "https://api.example.com/media/releases/livetv-android-v1.0.6-b7.apk",
                )

                release.refresh_from_db()
                self.assertEqual(
                    release.download_url,
                    "https://api.example.com/media/releases/livetv-android-v1.0.6-b7.apk",
                )
                self.assertNotIn("app-arm64-v8a-release", release.download_url)

    @override_settings(PUBLIC_API_URL="https://api.example.com")
    def test_resolved_download_url_ignores_stale_db_value(self):
        release = AppRelease(
            platform="android",
            version_name="1.0.6",
            build_number=7,
            download_url="https://api.example.com/media/livetv-android-v1.0.6-b7.apk",
        )
        release.apk_file.name = "releases/livetv-android-v1_KnM79xi.0.6-b7.apk"
        self.assertEqual(
            release.resolved_download_url(),
            "https://api.example.com/media/releases/livetv-android-v1_KnM79xi.0.6-b7.apk",
        )

    @override_settings(PUBLIC_API_URL="https://api.example.com")
    def test_reupload_keeps_canonical_filename_and_url(self):
        from django.core.files.storage import default_storage

        apk_bytes = b"PK fake apk v1"
        canonical = "releases/livetv-android-v1.0.6-b7.apk"
        mangled = "releases/livetv-android-v1_KnM79xi.0.6-b7.apk"
        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                default_storage.save(canonical, SimpleUploadedFile("old.apk", apk_bytes))
                default_storage.save(mangled, SimpleUploadedFile("old2.apk", apk_bytes))

                release = AppRelease(
                    platform="android",
                    version_name="1.0.6",
                    build_number=7,
                )
                release.apk_file = SimpleUploadedFile(
                    "app-arm64-v8a-release.apk",
                    b"PK fake apk v2",
                    content_type="application/vnd.android.package-archive",
                )
                release.save()

                self.assertEqual(release.apk_file.name, canonical)
                self.assertEqual(
                    release.download_url,
                    "https://api.example.com/media/releases/livetv-android-v1.0.6-b7.apk",
                )
                self.assertNotIn("_", release.apk_file.name.split("/")[-1])
