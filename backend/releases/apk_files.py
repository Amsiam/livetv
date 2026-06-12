from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files.storage import default_storage

if TYPE_CHECKING:
    from releases.models import AppRelease


def canonical_apk_basename(platform: str, version_name: str, build_number: int) -> str:
    return f"livetv-{platform}-v{version_name}-b{build_number}.apk"


def release_apk_upload_to(instance: AppRelease, filename: str) -> str:
    """Always store APKs under media/releases/ with a stable, versioned name."""
    del filename
    return f"releases/{canonical_apk_basename(instance.platform, instance.version_name, instance.build_number)}"


def clear_stale_apk_files(release: AppRelease) -> None:
    """Remove prior APK files for this platform/build (including mangled names)."""
    from pathlib import Path

    from django.conf import settings

    releases_dir = Path(settings.MEDIA_ROOT) / "releases"
    if not releases_dir.is_dir():
        return

    prefix = f"livetv-{release.platform}-v"
    build_token = f"-b{release.build_number}"
    for path in releases_dir.glob("*.apk"):
        if path.name.startswith(prefix) and build_token in path.name:
            storage_name = f"releases/{path.name}"
            if default_storage.exists(storage_name):
                default_storage.delete(storage_name)

