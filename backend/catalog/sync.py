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
from config.log_extra import log_extra

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
                    "Truncated display fields %s (name=%r len=%s)",
                    ", ".join(truncated_fields),
                    name[:80],
                    len(name),
                    extra=log_extra(
                        component="catalog.sync",
                        region=region,
                        truncated_fields=",".join(truncated_fields),
                        name_len=len(name),
                    ),
                )
                entry["_truncated_fields"] = truncated_fields
            yield entry


def upsert_catalog_entries(
    entries: list[dict],
    sync_started,
    *,
    region: str = "",
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
            batch_created, batch_updated = _upsert_batch(batch, region=region)
            created += batch_created
            updated += batch_updated
            batch.clear()

    if batch:
        batch_created, batch_updated = _upsert_batch(batch, region=region)
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

    logger.info(
        "Catalog sync region started",
        extra=log_extra(
            component="catalog.sync",
            region=region,
            verify_streams=verify_streams,
            deactivate_missing=deactivate_missing,
        ),
    )

    try:
        payload = fetch_region_payload(region)
    except requests.RequestException:
        logger.exception(
            "Failed to fetch region payload",
            extra=log_extra(component="catalog.sync", region=region),
        )
        result.errors += 1
        return result

    result.source_date = str(payload.get("date", ""))
    entries = list(iter_catalog_entries(payload, region))
    result.truncated = sum(1 for entry in entries if entry.get("_truncated_fields"))
    for entry in entries:
        entry.pop("_truncated_fields", None)

    logger.info(
        "Catalog sync region parsed upstream=%s entries=%s truncated=%s source_date=%s",
        region,
        len(entries),
        result.truncated,
        result.source_date,
        extra=log_extra(
            component="catalog.sync",
            region=region,
            entry_count=len(entries),
            truncated=result.truncated,
        ),
    )

    if verify_streams and entries:
        entries, skipped = filter_reachable_entries(entries)
        result.skipped = skipped
        if skipped:
            logger.info(
                "Skipped unreachable stream URLs in %s: %s",
                region,
                skipped,
                extra=log_extra(
                    component="catalog.sync",
                    region=region,
                    skipped=skipped,
                ),
            )

    try:
        result.created, result.updated = upsert_catalog_entries(
            entries,
            sync_started,
            region=region,
        )
    except Exception:
        logger.exception(
            "Catalog upsert failed for region %s",
            region,
            extra=log_extra(
                component="catalog.sync",
                region=region,
                entry_count=len(entries),
            ),
        )
        result.errors += 1
        return result

    if deactivate_missing:
        result.deactivated = finalize_region_sync(region, sync_started)

    if entries:
        linked = propagate_linked_match_channels(
            CatalogChannel.objects.filter(region=region, last_seen_at=sync_started)
        )
        if linked:
            logger.info(
                "Propagated catalog updates to %s match channel(s) in %s",
                linked,
                region,
                extra=log_extra(
                    component="catalog.sync",
                    region=region,
                    match_channels_updated=linked,
                ),
            )

    logger.info(
        "Catalog sync region finished created=%s updated=%s skipped=%s "
        "deactivated=%s truncated=%s errors=%s",
        result.created,
        result.updated,
        result.skipped,
        result.deactivated,
        result.truncated,
        result.errors,
        extra=log_extra(
            component="catalog.sync",
            region=region,
            created=result.created,
            updated=result.updated,
            skipped=result.skipped,
            deactivated=result.deactivated,
            truncated=result.truncated,
            errors=result.errors,
        ),
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


def _upsert_batch(batch: list[CatalogChannel], *, region: str = "") -> tuple[int, int]:
    existing = set(
        CatalogChannel.objects.filter(
            external_key__in=[item.external_key for item in batch]
        ).values_list("external_key", flat=True)
    )
    try:
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
    except Exception:
        sample = batch[0]
        logger.exception(
            "Catalog upsert batch failed size=%s sample_name=%r "
            "name_len=%s stream_url_len=%s category_len=%s",
            len(batch),
            sample.name[:120],
            len(sample.name),
            len(sample.stream_url),
            len(sample.category),
            extra=log_extra(
                component="catalog.sync",
                region=region or sample.region,
                batch_size=len(batch),
                name_len=len(sample.name),
                stream_url_len=len(sample.stream_url),
                category_len=len(sample.category),
                logo_url_len=len(sample.logo_url),
            ),
        )
        raise
    created = sum(1 for item in batch if item.external_key not in existing)
    updated = len(batch) - created
    logger.debug(
        "Catalog upsert batch ok created=%s updated=%s size=%s",
        created,
        updated,
        len(batch),
        extra=log_extra(
            component="catalog.sync",
            region=region or (batch[0].region if batch else ""),
            batch_size=len(batch),
            created=created,
            updated=updated,
        ),
    )
    return created, updated


def sync_regions(
    regions: list[str],
    deactivate_missing: bool = True,
    verify_streams: bool | None = None,
) -> CatalogSyncRun:
    run = CatalogSyncRun.objects.create(regions=regions)
    totals = RegionSyncResult(region="all")

    logger.info(
        "Catalog sync run started regions=%s sync_run_id=%s",
        ",".join(regions),
        run.id,
        extra=log_extra(
            component="catalog.sync",
            sync_run_id=str(run.id),
            regions=",".join(regions),
            region_count=len(regions),
        ),
    )

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

    logger.info(
        "Catalog sync run finished sync_run_id=%s created=%s updated=%s "
        "skipped=%s deactivated=%s truncated=%s errors=%s",
        run.id,
        run.created_count,
        run.updated_count,
        run.skipped_count,
        run.deactivated_count,
        totals.truncated,
        run.error_count,
        extra=log_extra(
            component="catalog.sync",
            sync_run_id=str(run.id),
            created=run.created_count,
            updated=run.updated_count,
            skipped=run.skipped_count,
            deactivated=run.deactivated_count,
            truncated=totals.truncated,
            errors=run.error_count,
        ),
    )

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
