"""Probe stream URLs and deactivate or reactivate catalog / match channels."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass

from django.conf import settings
from django.db.models import Q

from catalog.deactivation import DeactivationReason
from catalog.models import CatalogChannel
from health.stream_probe import probe_stream_url
from matches.models import Channel

PROBE_ACTIVE_LOCK_KEY = "health:probe_active_streams:running"
PROBE_LOCK_TTL = 60 * 60 * 4  # 4 hours — safety release if a worker dies

REACTIVATABLE_REASONS = frozenset(
    {
        DeactivationReason.USER_REPORTS,
        DeactivationReason.HEALTH_CHECK,
    }
)


def inactive_reactivation_queryset_filter() -> Q:
    """Inactive channels worth re-probing: below client failure threshold.

    Once ``failure_count`` reaches ``CHANNEL_FAILURE_THRESHOLD`` (default 100),
    Celery stops reactivation probes — the link is treated as confirmed dead.
    Health probes may deactivate sooner (``CHANNEL_HEALTH_FAILURE_THRESHOLD``=3),
    but recovery checks keep running until the client threshold is hit.
    Admin ``dead_link`` / ``admin`` reasons are never auto-reactivated.
    """
    client_threshold = settings.CHANNEL_FAILURE_THRESHOLD
    return Q(is_active=False) & Q(
        deactivation_reason__in=REACTIVATABLE_REASONS,
        failure_count__lt=client_threshold,
    )


@dataclass
class ChannelProbeStats:
    checked: int = 0
    failures: int = 0
    deactivated: int = 0

    def __add__(self, other: ChannelProbeStats) -> ChannelProbeStats:
        return ChannelProbeStats(
            checked=self.checked + other.checked,
            failures=self.failures + other.failures,
            deactivated=self.deactivated + other.deactivated,
        )


@dataclass
class ChannelReactivateStats:
    checked: int = 0
    reactivated: int = 0

    def __add__(self, other: ChannelReactivateStats) -> ChannelReactivateStats:
        return ChannelReactivateStats(
            checked=self.checked + other.checked,
            reactivated=self.reactivated + other.reactivated,
        )


@dataclass
class StreamMaintenanceResult:
    match_channels: ChannelProbeStats
    tv_channels: ChannelProbeStats

    def to_dict(self) -> dict:
        return {
            "match_channels": asdict(self.match_channels),
            "tv_channels": asdict(self.tv_channels),
        }


@dataclass
class StreamReactivateResult:
    match_channels: ChannelReactivateStats
    tv_channels: ChannelReactivateStats

    def to_dict(self) -> dict:
        return {
            "match_channels": asdict(self.match_channels),
            "tv_channels": asdict(self.tv_channels),
        }


def _url_probeable(url: str) -> bool:
    return bool(url and url.strip().startswith(("http://", "https://")))


def _parse_uuid_list(channel_ids: list[str]) -> list[uuid.UUID]:
    return [uuid.UUID(value) for value in channel_ids]


def _probe_workers(workers: int | None, item_count: int) -> int:
    configured = workers if workers is not None else settings.STREAM_PROBE_WORKERS
    return max(1, min(configured, item_count or 1))


def _probe_urls_parallel(
    items: list[tuple[object, str]],
    *,
    timeout: int,
    workers: int | None = None,
) -> dict[object, bool]:
    if not items:
        return {}

    pool_size = _probe_workers(workers, len(items))
    results: dict[object, bool] = {}
    with ThreadPoolExecutor(max_workers=pool_size) as pool:
        futures = {
            pool.submit(probe_stream_url, url, timeout): channel
            for channel, url in items
        }
        for future in as_completed(futures):
            channel = futures[future]
            try:
                results[channel] = future.result()
            except Exception:
                results[channel] = False
    return results


def _apply_probe_results(
    probe_results: dict[object, bool],
    *,
    failure_source: str,
) -> ChannelProbeStats:
    stats = ChannelProbeStats()
    for channel, ok in probe_results.items():
        stats.checked += 1
        if ok:
            channel.record_success()
            continue
        stats.failures += 1
        if channel.record_failure(source=failure_source):
            stats.deactivated += 1
    return stats


def probe_match_channel_ids(
    channel_ids: list[str],
    *,
    timeout: int = 5,
    workers: int | None = None,
) -> ChannelProbeStats:
    if not channel_ids:
        return ChannelProbeStats()

    ids = _parse_uuid_list(channel_ids)
    channels = list(Channel.objects.filter(id__in=ids, is_active=True))
    items = [
        (channel, channel.stream_url)
        for channel in channels
        if _url_probeable(channel.stream_url)
    ]
    probe_results = _probe_urls_parallel(items, timeout=timeout, workers=workers)
    return _apply_probe_results(probe_results, failure_source="health_check")


def probe_tv_channel_ids(
    channel_ids: list[str],
    *,
    timeout: int = 5,
    workers: int | None = None,
) -> ChannelProbeStats:
    if not channel_ids:
        return ChannelProbeStats()

    ids = _parse_uuid_list(channel_ids)
    channels = list(CatalogChannel.objects.filter(id__in=ids, is_active=True))
    items = [
        (channel, channel.stream_url)
        for channel in channels
        if _url_probeable(channel.stream_url)
    ]
    probe_results = _probe_urls_parallel(items, timeout=timeout, workers=workers)
    return _apply_probe_results(probe_results, failure_source="health_check")


def reactivate_match_channel_ids(
    channel_ids: list[str],
    *,
    timeout: int = 5,
    workers: int | None = None,
) -> ChannelReactivateStats:
    stats = ChannelReactivateStats()
    if not channel_ids:
        return stats

    ids = _parse_uuid_list(channel_ids)
    channels = list(
        Channel.objects.filter(id__in=ids).filter(inactive_reactivation_queryset_filter())
    )
    items = [
        (channel, channel.stream_url)
        for channel in channels
        if _url_probeable(channel.stream_url)
    ]
    probe_results = _probe_urls_parallel(items, timeout=timeout, workers=workers)
    for channel, ok in probe_results.items():
        stats.checked += 1
        if ok:
            channel.admin_reactivate()
            stats.reactivated += 1
    return stats


def reactivate_tv_channel_ids(
    channel_ids: list[str],
    *,
    timeout: int = 5,
    workers: int | None = None,
) -> ChannelReactivateStats:
    stats = ChannelReactivateStats()
    if not channel_ids:
        return stats

    ids = _parse_uuid_list(channel_ids)
    channels = list(
        CatalogChannel.objects.filter(id__in=ids).filter(
            inactive_reactivation_queryset_filter()
        )
    )
    items = [
        (channel, channel.stream_url)
        for channel in channels
        if _url_probeable(channel.stream_url)
    ]
    probe_results = _probe_urls_parallel(items, timeout=timeout, workers=workers)
    for channel, ok in probe_results.items():
        stats.checked += 1
        if ok:
            channel.admin_reactivate()
            stats.reactivated += 1
    return stats


def probe_active_streams(*, timeout: int = 5, workers: int | None = None) -> StreamMaintenanceResult:
    """Probe all active channels (CLI / synchronous)."""
    match_ids = [
        str(pk)
        for pk in Channel.objects.filter(is_active=True)
        .order_by("-failure_count")
        .values_list("id", flat=True)
    ]
    tv_ids = [
        str(pk)
        for pk in CatalogChannel.objects.filter(is_active=True)
        .order_by("-failure_count")
        .values_list("id", flat=True)
    ]
    return StreamMaintenanceResult(
        match_channels=probe_match_channel_ids(match_ids, timeout=timeout, workers=workers),
        tv_channels=probe_tv_channel_ids(tv_ids, timeout=timeout, workers=workers),
    )


def reactivate_recovered_streams(*, timeout: int = 5, workers: int | None = None) -> StreamReactivateResult:
    """Reactivate inactive channels that are below failure threshold (CLI / synchronous)."""
    match_ids = [
        str(pk)
        for pk in Channel.objects.filter(inactive_reactivation_queryset_filter()).values_list(
            "id", flat=True
        )
    ]
    tv_ids = [
        str(pk)
        for pk in CatalogChannel.objects.filter(
            inactive_reactivation_queryset_filter()
        ).values_list("id", flat=True)
    ]
    return StreamReactivateResult(
        match_channels=reactivate_match_channel_ids(match_ids, timeout=timeout, workers=workers),
        tv_channels=reactivate_tv_channel_ids(tv_ids, timeout=timeout, workers=workers),
    )


def collect_active_channel_id_chunks(
    *,
    chunk_size: int,
) -> tuple[list[list[str]], list[list[str]]]:
    from health.chunking import chunk_list

    match_ids = [
        str(pk)
        for pk in Channel.objects.filter(is_active=True)
        .order_by("-failure_count")
        .values_list("id", flat=True)
    ]
    tv_ids = [
        str(pk)
        for pk in CatalogChannel.objects.filter(is_active=True)
        .order_by("-failure_count")
        .values_list("id", flat=True)
    ]
    return chunk_list(match_ids, chunk_size), chunk_list(tv_ids, chunk_size)


def collect_inactive_channel_id_chunks(
    *,
    chunk_size: int,
) -> tuple[list[list[str]], list[list[str]]]:
    from health.chunking import chunk_list

    match_ids = [
        str(pk)
        for pk in Channel.objects.filter(inactive_reactivation_queryset_filter()).values_list(
            "id", flat=True
        )
    ]
    tv_ids = [
        str(pk)
        for pk in CatalogChannel.objects.filter(
            inactive_reactivation_queryset_filter()
        ).values_list("id", flat=True)
    ]
    return chunk_list(match_ids, chunk_size), chunk_list(tv_ids, chunk_size)
