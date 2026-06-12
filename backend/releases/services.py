from releases.cache import get_cached_latest_release
from releases.models import AppPlatform, AppRelease


def latest_published_release(platform: str) -> AppRelease | None:
    return get_cached_latest_release(platform)


def evaluate_app_update(
    *,
    platform: str,
    current_build: int,
    release: AppRelease | None = None,
) -> dict:
    if release is None:
        release = latest_published_release(platform)
    if release is None:
        return {
            "update_available": False,
            "force_update": False,
            "version_name": "",
            "build_number": current_build,
            "min_build_number": current_build,
            "download_url": "",
            "release_notes": "",
        }

    update_available = current_build < release.build_number
    below_minimum = current_build < release.min_build_number
    force_update = below_minimum or (release.force_update and update_available)

    return {
        "update_available": update_available,
        "force_update": force_update,
        "version_name": release.version_name,
        "build_number": release.build_number,
        "min_build_number": release.min_build_number,
        "download_url": release.resolved_download_url(),
        "release_notes": release.release_notes,
    }
