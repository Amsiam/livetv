"""Redis-backed TV channel view counters with periodic DB flush."""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db.models import F

logger = logging.getLogger(__name__)

PENDING_HASH = "tv:channel_views:pending"
RANK_ZSET = "tv:channel_views:rank"
FLUSH_LOCK_KEY = "tv:channel_views:flush:lock"
FLUSH_LOCK_TTL = 60 * 10


def redis_view_counts_enabled() -> bool:
    return bool(getattr(settings, "REDIS_URL", ""))


def _redis_client():
    if not redis_view_counts_enabled():
        return None
    from django_redis import get_redis_connection

    return get_redis_connection("default")


def _channel_key(channel_id) -> str:
    return str(channel_id)


def record_channel_view(channel_id, *, db_count: int) -> tuple[int, bool]:
    """Increment view count in Redis. Returns (effective_count, recorded)."""
    client = _redis_client()
    key = _channel_key(channel_id)
    if client is None:
        from catalog.models import CatalogChannel

        CatalogChannel.objects.filter(pk=channel_id).update(
            view_count=F("view_count") + 1
        )
        return db_count + 1, True

    if client.zscore(RANK_ZSET, key) is None:
        pipe = client.pipeline()
        pipe.zadd(RANK_ZSET, {key: db_count + 1})
        pipe.hincrby(PENDING_HASH, key, 1)
        pipe.execute()
        return db_count + 1, True

    pipe = client.pipeline()
    pipe.hincrby(PENDING_HASH, key, 1)
    pipe.zincrby(RANK_ZSET, 1, key)
    _, new_score = pipe.execute()
    return int(new_score), True


def effective_view_count(channel_id, *, db_count: int) -> int:
    client = _redis_client()
    if client is None:
        return db_count
    score = client.zscore(RANK_ZSET, _channel_key(channel_id))
    if score is None:
        return db_count
    return int(score)


def batch_effective_view_counts(db_counts: dict[str, int]) -> dict[str, int]:
    if not db_counts:
        return {}

    client = _redis_client()
    if client is None:
        return dict(db_counts)

    keys = list(db_counts.keys())
    pipe = client.pipeline()
    for key in keys:
        pipe.zscore(RANK_ZSET, key)
    scores = pipe.execute()

    result: dict[str, int] = {}
    for key, score in zip(keys, scores):
        result[key] = int(score) if score is not None else db_counts[key]
    return result


def flush_pending_view_counts_to_db() -> dict:
    """Move pending Redis increments into PostgreSQL."""
    client = _redis_client()
    if client is None:
        return {"status": "skipped", "reason": "redis_unavailable", "flushed": 0, "channels": 0}

    if not client.set(FLUSH_LOCK_KEY, "1", nx=True, ex=FLUSH_LOCK_TTL):
        return {"status": "skipped", "reason": "locked", "flushed": 0, "channels": 0}

    processing_key = f"{PENDING_HASH}:processing:{uuid.uuid4().hex}"
    try:
        if not client.exists(PENDING_HASH):
            return {"status": "ok", "flushed": 0, "channels": 0}

        client.rename(PENDING_HASH, processing_key)
        raw_pending = client.hgetall(processing_key)
        if not raw_pending:
            client.delete(processing_key)
            return {"status": "ok", "flushed": 0, "channels": 0}

        from catalog.models import CatalogChannel

        flushed = 0
        channels = 0
        for raw_id, raw_count in raw_pending.items():
            channel_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            count = int(raw_count)
            if count <= 0:
                continue
            updated = CatalogChannel.objects.filter(pk=channel_id).update(
                view_count=F("view_count") + count
            )
            if updated:
                channels += 1
                flushed += count

        client.delete(processing_key)
        logger.info("Flushed %s channel views across %s channels", flushed, channels)
        return {"status": "ok", "flushed": flushed, "channels": channels}
    finally:
        client.delete(FLUSH_LOCK_KEY)
