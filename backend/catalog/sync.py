import logging
from dataclasses import dataclass
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone

from catalog.deactivation import DeactivationReason
from catalog.models import (
    CatalogChannel,
    CatalogSyncRun,
    make_external_key,
    make_group_key,
)
from catalog.normalize import fit_catalog_entry
from catalog.probe import filter_reachable_entries
from catalog.stream_urls import is_hls_stream_url

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


@dataclass
class RegionSyncResult:
    region: str
    created: int = 0
    updated: int = 0
    deactivated: int = 0
    skipped: int = 0
    truncated: int = 0
    errors: int = 0
    source_date: str = ""


def collector_base_url() -> str:
    return getattr(
        settings,
        "LIVETV_COLLECTOR_BASE_URL",
        "https://raw.githubusercontent.com/bugsfreeweb/LiveTVCollector/main/LiveTV",
    ).rstrip("/")


def fetch_region_list() -> list[str]:
    response = requests.get(f"{collector_base_url()}/index.json", timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_region_payload(region: str) -> dict:
    url = f"{collector_base_url()}/{region}/LiveTV.json"
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    return response.json()


def iter_catalog_entries(payload: dict, region: str):
    channels_by_group = payload.get("channels") or {}
    source_date = str(payload.get("date", ""))
    for group_name, items in channels_by_group.items():
        if not isinstance(items, list):
            continue
        for item in items:
            name = (item.get("name") or "").strip()
            stream_url = (item.get("url") or "").strip()
            if not name or not stream_url:
                continue
            if not is_hls_stream_url(stream_url):
                continue
            category = (item.get("group") or group_name or "").strip()
            entry, truncated_fields = fit_catalog_entry(
                {
                    "external_key": make_external_key(region, name, stream_url),
                    "group_key": make_group_key(name),
                    "region": region,
                    "category": category,
                    "name": name,
                    "logo_url": (item.get("logo") or "").strip(),
                    "stream_url": stream_url,
                    "source_url": (item.get("source") or "").strip(),
                    "source_date": source_date,
                }
            )
            if truncated_fields:
                logger.warning(
                    "Truncated catalog fields %s for %r in %s",
                    ", ".join(truncated_fields),
                    name[:80],
                    region,
                )
                entry["_truncated_fields"] = truncated_fields
            yield entry


def upsert_catalog_entries(
    entries: list[dict],
    sync_started,
) -> tuple[int, int]:
    """Upsert catalog rows in batches. Returns (created, updated)."""
    created = 0
    updated = 0
    batch: list[CatalogChannel] = []
    chunk_size = getattr(settings, "CATALOG_SYNC_CHUNK_SIZE", BATCH_SIZE)

    for entry in entries:
        entry.pop("_truncated_fields", None)
        batch.append(
            CatalogChannel(
                external_key=entry["external_key"],
                group_key=entry["group_key"],
                region=entry["region"],
                category=entry["category"],
                name=entry["name"],
                logo_url=entry["logo_url"],
                stream_url=entry["stream_url"],
                source_url=entry["source_url"],
                source_date=entry["source_date"],
                is_active=True,
                last_seen_at=sync_started,
            )
        )

        if len(batch) >= chunk_size:
            batch_created, batch_updated = _upsert_batch(batch)
            created += batch_created
            updated += batch_updated
            batch.clear()

    if batch:
        batch_created, batch_updated = _upsert_batch(batch)
        created += batch_created
        updated += batch_updated

    return created, updated


def deactivate_non_hls_channels(region: str) -> int:
    """Deactivate active catalog rows whose stream URL is not HLS (e.g. MP4)."""
    now = timezone.now()
    return (
        CatalogChannel.objects.filter(region=region, is_active=True)
        .exclude(stream_url__icontains="m3u8")
        .update(
            is_active=False,
            deactivation_reason=DeactivationReason.UNSUPPORTED_FORMAT,
            deactivated_at=now,
            updated_at=now,
        )
    )


def finalize_region_sync(
    region: str,
    sync_started,
    *,
    deactivate_missing: bool = True,
) -> int:
    """Deactivate missing sync rows and non-HLS stream URLs in a region."""
    now = timezone.now()
    deactivated = deactivate_non_hls_channels(region)

    if not deactivate_missing:
        return deactivated

    deactivated += CatalogChannel.objects.filter(
        region=region,
        is_active=True,
        last_seen_at__lt=sync_started,
    ).update(
        is_active=False,
        deactivation_reason=DeactivationReason.SYNC_MISSING,
        deactivated_at=now,
        updated_at=now,
    )
    return deactivated


def sync_region(
    region: str,
    deactivate_missing: bool = True,
    verify_streams: bool | None = None,
) -> RegionSyncResult:
    result = RegionSyncResult(region=region)
    sync_started = timezone.now()

    if verify_streams is None:
        verify_streams = getattr(settings, "CATALOG_SYNC_PROBE_STREAMS", False)

    try:
        payload = fetch_region_payload(region)
    except requests.RequestException:
        logger.exception("Failed to fetch region %s", region)
        result.errors += 1
        return result

    result.source_date = str(payload.get("date", ""))
    entries = list(iter_catalog_entries(payload, region))
    result.truncated = sum(1 for entry in entries if entry.get("_truncated_fields"))
    for entry in entries:
        entry.pop("_truncated_fields", None)

    if verify_streams and entries:
        entries, skipped = filter_reachable_entries(entries)
        result.skipped = skipped
        if skipped:
            logger.info("Region %s: skipped %s unreachable stream URLs", region, skipped)

    result.created, result.updated = upsert_catalog_entries(entries, sync_started)

    if deactivate_missing:
        result.deactivated = finalize_region_sync(region, sync_started)

    if entries:
        propagate_linked_match_channels(
            CatalogChannel.objects.filter(region=region, last_seen_at=sync_started)
        )

    return result


def propagate_linked_match_channels(catalog_qs) -> int:
    """Push catalog stream/metadata updates to linked match channels."""
    from matches.models import Channel

    updated = 0
    for catalog in catalog_qs.filter(
        is_active=True,
        match_channels__isnull=False,
    ).distinct().iterator():
        count = Channel.objects.filter(
            catalog_channel=catalog,
            follow_catalog_stream=True,
        ).update(
            stream_url=catalog.stream_url,
            logo_url=catalog.logo_url,
            name=catalog.name,
            url_updated_at=timezone.now(),
            updated_at=timezone.now(),
        )
        updated += count
    return updated


def _upsert_batch(batch: list[CatalogChannel]) -> tuple[int, int]:
    existing = set(
        CatalogChannel.objects.filter(
            external_key__in=[item.external_key for item in batch]
        ).values_list("external_key", flat=True)
    )
    CatalogChannel.objects.bulk_create(
        batch,
        update_conflicts=True,
        unique_fields=["external_key"],
        update_fields=[
            "group_key",
            "region",
            "category",
            "name",
            "logo_url",
            "stream_url",
            "source_url",
            "source_date",
            "last_seen_at",
            "updated_at",
        ],
    )
    created = sum(1 for item in batch if item.external_key not in existing)
    updated = len(batch) - created
    return created, updated


def sync_regions(
    regions: list[str],
    deactivate_missing: bool = True,
    verify_streams: bool | None = None,
) -> CatalogSyncRun:
    run = CatalogSyncRun.objects.create(regions=regions)
    totals = RegionSyncResult(region="all")

    for region in regions:
        result = sync_region(
            region,
            deactivate_missing=deactivate_missing,
            verify_streams=verify_streams,
        )
        totals.created += result.created
        totals.updated += result.updated
        totals.deactivated += result.deactivated
        totals.skipped += result.skipped
        totals.truncated += result.truncated
        totals.errors += result.errors

    run.created_count = totals.created
    run.updated_count = totals.updated
    run.deactivated_count = totals.deactivated
    run.skipped_count = totals.skipped
    run.error_count = totals.errors
    run.finished_at = timezone.now()
    run.notes = f"Completed at {datetime.now().isoformat(timespec='seconds')}"
    run.save()

    from catalog.cache import invalidate_catalog_caches

    invalidate_catalog_caches()
    return run


def resolve_regions(explicit: list[str] | None = None, sync_all: bool = False) -> list[str]:
    if sync_all:
        return fetch_region_list()
    if explicit:
        return explicit
    configured = getattr(settings, "LIVETV_COLLECTOR_REGIONS", "")
    if configured:
        return [r.strip() for r in configured.split(",") if r.strip()]
    return ["Bangladesh"]
