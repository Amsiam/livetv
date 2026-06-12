from django.core.cache import cache

MATCH_LIST_PREFIX = "matches:list"
MATCH_DETAIL_PREFIX = "matches:detail"
CHANNEL_LIST_PREFIX = "matches:channels"


def _delete_pattern(pattern: str) -> None:
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)
        return

    # LocMemCache fallback: clear entire cache when pattern invalidation unavailable.
    cache.clear()


def invalidate_match_caches(match_id=None) -> None:
    _delete_pattern(f"{MATCH_LIST_PREFIX}:*")
    if match_id:
        cache.delete(f"{MATCH_DETAIL_PREFIX}:{match_id}")
        cache.delete(f"{CHANNEL_LIST_PREFIX}:{match_id}")
    else:
        _delete_pattern(f"{MATCH_DETAIL_PREFIX}:*")
        _delete_pattern(f"{CHANNEL_LIST_PREFIX}:*")
