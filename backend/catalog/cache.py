from django.core.cache import cache

CATALOG_LIST_PREFIX = "tv-channels:list"
CATALOG_DETAIL_PREFIX = "tv-channels:detail"
CATALOG_REGIONS_KEY = "tv-channels:regions"


def _delete_pattern(pattern: str) -> None:
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)
        return
    cache.clear()


def invalidate_catalog_caches(channel_id=None) -> None:
    _delete_pattern(f"{CATALOG_LIST_PREFIX}:*")
    cache.delete(CATALOG_REGIONS_KEY)
    if channel_id:
        cache.delete(f"{CATALOG_DETAIL_PREFIX}:{channel_id}")
    else:
        _delete_pattern(f"{CATALOG_DETAIL_PREFIX}:*")
