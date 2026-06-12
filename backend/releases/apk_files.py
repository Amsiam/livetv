from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files import File
from django.core.files.storage import default_storage

if TYPE_CHECKING:
    from releases.models import AppRelease


def canonical_apk_basename(platform: str, version_name: str, build_number: int) -> str:
    return f"livetv-{platform}-v{version_name}-b{build_number}.apk"


def release_apk_upload_to(instance: AppRelease, filename: str) -> str:
    """Always store APKs under media/releases/ with a stable, versioned name."""
    del filename
    return f"releases/{canonical_apk_basename(instance.platform, instance.version_name, instance.build_number)}"


def store_canonical_apk(release: AppRelease) -> None:
    """Rename legacy uploads to the canonical releases/ path (no model save)."""
    if not release.apk_file:
        return

    storage_name = release_apk_upload_to(release, "")
    if release.apk_file.name == storage_name:
        return

    old_name = release.apk_file.name
    canonical = storage_name.rsplit("/", 1)[-1]
    with release.apk_file.open("rb") as handle:
        release.apk_file.save(canonical, File(handle), save=False)

    if old_name and old_name != release.apk_file.name and default_storage.exists(old_name):
        default_storage.delete(old_name)
