import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from releases.models import AppRelease
from releases.pubspec import parse_pubspec_version


class PublishAppReleaseTests(TestCase):
    def test_parse_pubspec_version(self):
        pubspec = Path(__file__).resolve().parents[2] / "app" / "pubspec.yaml"
        version_name, build = parse_pubspec_version(pubspec)
        self.assertEqual(version_name, "1.0.0")
        self.assertEqual(build, 1)

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
