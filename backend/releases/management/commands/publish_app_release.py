from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from releases.apk_files import canonical_apk_basename
from releases.models import AppPlatform, AppRelease
from releases.pubspec import parse_pubspec_version


class Command(BaseCommand):
    help = (
        "Store an APK under media/releases/ and create or update an App release row "
        "(sets download_url for in-app updates)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apk",
            required=True,
            help="Path to the built .apk file.",
        )
        parser.add_argument(
            "--platform",
            default=AppPlatform.ANDROID,
            choices=AppPlatform.values,
        )
        parser.add_argument(
            "--pubspec",
            help="Path to pubspec.yaml (reads version name + build number).",
        )
        parser.add_argument("--version-name", help="Override version name, e.g. 1.0.1")
        parser.add_argument("--build-number", type=int, help="Override Flutter build number")
        parser.add_argument(
            "--min-build-number",
            type=int,
            default=1,
            help="Users below this build are forced to update.",
        )
        parser.add_argument("--force-update", action="store_true")
        parser.add_argument("--notes", default="", help="Release notes shown in the app")
        parser.add_argument(
            "--unpublished",
            action="store_true",
            help="Create the row but leave is_published=false.",
        )

    def handle(self, *args, **options):
        apk_path = Path(options["apk"]).expanduser().resolve()
        if not apk_path.is_file():
            raise CommandError(f"APK not found: {apk_path}")
        if apk_path.suffix.lower() != ".apk":
            raise CommandError(f"Expected a .apk file: {apk_path}")

        version_name = options["version_name"]
        build_number = options["build_number"]
        if options["pubspec"]:
            parsed_name, parsed_build = parse_pubspec_version(options["pubspec"])
            version_name = version_name or parsed_name
            build_number = build_number if build_number is not None else parsed_build

        if not version_name or build_number is None:
            raise CommandError(
                "Provide --pubspec or both --version-name and --build-number."
            )

        if not settings.PUBLIC_API_URL:
            self.stdout.write(
                self.style.WARNING(
                    "PUBLIC_API_URL is not set — download_url will use "
                    "http://127.0.0.1:8000 in DEBUG. Phones cannot reach that. "
                    "Set PUBLIC_API_URL to your tunnel or public API origin."
                )
            )

        platform = options["platform"]
        filename = canonical_apk_basename(platform, version_name, build_number)

        release, created = AppRelease.objects.update_or_create(
            platform=platform,
            build_number=build_number,
            defaults={
                "version_name": version_name,
                "min_build_number": options["min_build_number"],
                "force_update": options["force_update"],
                "release_notes": options["notes"],
                "is_published": not options["unpublished"],
            },
        )

        if release.apk_file:
            release.apk_file.delete(save=False)

        Path(settings.MEDIA_ROOT, "releases").mkdir(parents=True, exist_ok=True)
        with apk_path.open("rb") as handle:
            release.apk_file.save(filename, File(handle), save=False)

        release.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {platform} release {version_name} (build {build_number})\n"
                f"  download_url: {release.download_url}\n"
                f"  file: {release.apk_file.name}"
            )
        )
