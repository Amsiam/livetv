from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import cache

if TYPE_CHECKING:
    from releases.models import AppRelease

_LATEST_RELEASE_PREFIX = "app_release:latest"
_EMPTY = "__empty__"


def latest_release_cache_key(platform: str) -> str:
    return f"{_LATEST_RELEASE_PREFIX}:{platform}"


def invalidate_latest_release_cache(platform: str) -> None:
    cache.delete(latest_release_cache_key(platform))


def get_cached_latest_release(platform: str) -> AppRelease | None:
    from releases.models import AppRelease

    key = latest_release_cache_key(platform)
    cached = cache.get(key)
    if cached == _EMPTY:
        return None
    if isinstance(cached, AppRelease):
        return cached

    release = (
        AppRelease.objects.filter(platform=platform, is_published=True)
        .order_by("-build_number")
        .first()
    )
    cache.set(
        key,
        release if release is not None else _EMPTY,
        settings.APP_UPDATE_CACHE_TTL,
    )
    return release
