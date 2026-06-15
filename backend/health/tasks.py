import json
import logging

from celery import chord, group, shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from config.log_extra import log_extra

logger = logging.getLogger(__name__)

SYNC_CATALOG_LOCK_KEY = "health:sync_tv_catalog:running"
SYNC_CATALOG_LOCK_TTL = 60 * 60 * 4  # safety release if workers die mid-sync


def _release_sync_catalog_lock() -> None:
    from django.core.cache import cache

    cache.delete(SYNC_CATALOG_LOCK_KEY)


def _parse_sync_started(sync_started_iso: str):
    parsed = parse_datetime(sync_started_iso)
    if parsed is None:
        raise ValueError(f"Invalid sync_started timestamp: {sync_started_iso}")
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _record_region_sync_result(sync_run_id: str, region: str, result: dict) -> None:
    from catalog.cache import invalidate_catalog_caches
    from catalog.models import CatalogSyncRun

    finished = False
    with transaction.atomic():
        run = CatalogSyncRun.objects.select_for_update().get(pk=sync_run_id)
        run.created_count = F("created_count") + result.get("created", 0)
        run.updated_count = F("updated_count") + result.get("updated", 0)
        run.deactivated_count = F("deactivated_count") + result.get("deactivated", 0)
        run.skipped_count = F("skipped_count") + result.get("skipped", 0)
        run.error_count = F("error_count") + result.get("errors", 0)
        run.save(
            update_fields=[
                "created_count",
                "updated_count",
                "deactivated_count",
                "skipped_count",
                "error_count",
            ]
        )
        run.refresh_from_db()

        notes = json.loads(run.notes or "{}")
        completed = set(notes.get("completed_regions", []))
        completed.add(region)
        notes["completed_regions"] = sorted(completed)
        run.notes = json.dumps(notes)
        if len(completed) >= len(run.regions):
            run.finished_at = timezone.now()
            finished = True
        run.save(update_fields=["notes", "finished_at"])

    if finished:
        _release_sync_catalog_lock()
        invalidate_catalog_caches()
        run = CatalogSyncRun.objects.get(pk=sync_run_id)
        logger.info(
            "Catalog sync run finished sync_run_id=%s created=%s updated=%s "
            "skipped=%s deactivated=%s errors=%s regions=%s",
            sync_run_id,
            run.created_count,
            run.updated_count,
            run.skipped_count,
            run.deactivated_count,
            run.error_count,
            ",".join(run.regions),
            extra=log_extra(
                component="health.sync",
                sync_run_id=sync_run_id,
                created=run.created_count,
                updated=run.updated_count,
                skipped=run.skipped_count,
                deactivated=run.deactivated_count,
                errors=run.error_count,
            ),
        )


@shared_task(name="health.sync_tv_catalog")
def sync_tv_catalog_task() -> dict:
    """Dispatch per-region catalog sync coordinators."""
    from django.core.cache import cache

    from catalog.models import CatalogSyncRun
    from catalog.sync import resolve_regions

    if not cache.add(SYNC_CATALOG_LOCK_KEY, "1", timeout=SYNC_CATALOG_LOCK_TTL):
        logger.warning(
            "Catalog sync skipped — another sync is already running",
            extra=log_extra(component="health.sync", reason="sync_in_progress"),
        )
        return {"status": "skipped", "reason": "sync_in_progress"}

    regions = resolve_regions()
    run = CatalogSyncRun.objects.create(regions=regions)
    try:
        for region in regions:
            sync_region_coordinator_task.delay(str(run.id), region)
    except Exception:
        _release_sync_catalog_lock()
        logger.exception(
            "Catalog sync dispatch failed",
            extra=log_extra(
                component="health.sync",
                sync_run_id=str(run.id),
            ),
        )
        run.error_count = 1
        run.finished_at = timezone.now()
        run.notes = json.dumps({"error": "dispatch_failed"})
        run.save(update_fields=["error_count", "finished_at", "notes"])
        raise

    result = {
        "sync_run_id": str(run.id),
        "regions": regions,
        "status": "dispatched",
    }
    logger.info(
        "Catalog sync dispatched sync_run_id=%s regions=%s",
        run.id,
        ",".join(regions),
        extra=log_extra(
            component="health.sync",
            sync_run_id=str(run.id),
            regions=",".join(regions),
            region_count=len(regions),
        ),
    )
    return result


@shared_task(name="health.sync_region_coordinator")
def sync_region_coordinator_task(sync_run_id: str, region: str) -> dict:
    """Fetch one region and dispatch chunked upsert tasks."""
    import requests

    from catalog.sync import fetch_region_payload, iter_catalog_entries
    from health.chunking import chunk_list

    sync_started = timezone.now()
    sync_started_iso = sync_started.isoformat()

    try:
        payload = fetch_region_payload(region)
    except requests.RequestException:
        logger.exception(
            "Failed to fetch region payload",
            extra=log_extra(
                component="health.sync",
                sync_run_id=sync_run_id,
                region=region,
            ),
        )
        _record_region_sync_result(
            sync_run_id,
            region,
            {"errors": 1},
        )
        return {"region": region, "status": "error"}

    entries = list(iter_catalog_entries(payload, region))
    chunk_size = settings.CATALOG_SYNC_CHUNK_SIZE
    chunks = chunk_list(entries, chunk_size)

    logger.info(
        "Catalog sync region dispatched entries=%s chunks=%s",
        len(entries),
        len(chunks),
        extra=log_extra(
            component="health.sync",
            sync_run_id=sync_run_id,
            region=region,
            entry_count=len(entries),
            chunk_count=len(chunks),
        ),
    )

    if not chunks:
        finalize_region_sync_task.apply_async(
            args=[[], sync_run_id, region, sync_started_iso],
        )
        return {"region": region, "chunks": 0, "entries": 0, "status": "dispatched"}

    header = [
        sync_region_entries_chunk_task.s(region, chunk, sync_started_iso, sync_run_id)
        for chunk in chunks
    ]
    callback = finalize_region_sync_task.s(sync_run_id, region, sync_started_iso)
    chord(header)(callback)

    return {
        "region": region,
        "chunks": len(chunks),
        "entries": len(entries),
        "status": "dispatched",
    }


@shared_task(name="health.sync_region_entries_chunk")
def sync_region_entries_chunk_task(
    region: str,
    entries: list[dict],
    sync_started_iso: str,
    sync_run_id: str,
) -> dict:
    from catalog.sync import upsert_catalog_entries

    sync_started = _parse_sync_started(sync_started_iso)
    try:
        created, updated = upsert_catalog_entries(
            entries,
            sync_started,
            region=region,
        )
    except Exception:
        logger.exception(
            "Catalog sync chunk failed",
            extra=log_extra(
                component="health.sync",
                sync_run_id=sync_run_id,
                region=region,
                chunk_size=len(entries),
            ),
        )
        # Chord callback will not run after a header failure — mark region so the
        # sync run can still reach finished_at instead of staying at 0 forever.
        _record_region_sync_result(sync_run_id, region, {"errors": 1})
        raise
    return {
        "region": region,
        "created": created,
        "updated": updated,
    }


@shared_task(name="health.finalize_region_sync")
def finalize_region_sync_task(
    chunk_results: list[dict],
    sync_run_id: str,
    region: str,
    sync_started_iso: str,
) -> dict:
    from catalog.sync import finalize_region_sync, propagate_linked_match_channels
    from catalog.models import CatalogChannel

    sync_started = _parse_sync_started(sync_started_iso)
    created = sum(item.get("created", 0) for item in chunk_results)
    updated = sum(item.get("updated", 0) for item in chunk_results)
    deactivated = finalize_region_sync(region, sync_started)

    if created or updated:
        propagate_linked_match_channels(
            CatalogChannel.objects.filter(region=region, last_seen_at=sync_started)
        )

    result = {
        "region": region,
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
    }
    _record_region_sync_result(sync_run_id, region, result)
    logger.info(
        "Catalog sync region finalized created=%s updated=%s deactivated=%s",
        created,
        updated,
        deactivated,
        extra=log_extra(
            component="health.sync",
            sync_run_id=sync_run_id,
            region=region,
            created=created,
            updated=updated,
            deactivated=deactivated,
        ),
    )
    return result


@shared_task(name="health.probe_match_channels_chunk")
def probe_match_channels_chunk_task(
    channel_ids: list[str],
    timeout: int,
    workers: int,
) -> dict:
    from health.stream_health import probe_match_channel_ids

    stats = probe_match_channel_ids(
        channel_ids,
        timeout=timeout,
        workers=workers,
    )
    return {"type": "match", **stats.__dict__}


@shared_task(name="health.probe_tv_channels_chunk")
def probe_tv_channels_chunk_task(
    channel_ids: list[str],
    timeout: int,
    workers: int,
) -> dict:
    from health.stream_health import probe_tv_channel_ids

    stats = probe_tv_channel_ids(
        channel_ids,
        timeout=timeout,
        workers=workers,
    )
    return {"type": "tv", **stats.__dict__}


@shared_task(name="health.probe_wave_finished")
def probe_wave_finished_task(chunk_results: list[dict]) -> dict:
    from django.core.cache import cache

    from health.stream_health import PROBE_ACTIVE_LOCK_KEY

    cache.delete(PROBE_ACTIVE_LOCK_KEY)
    failures = sum(item.get("failures", 0) for item in chunk_results)
    deactivated = sum(item.get("deactivated", 0) for item in chunk_results)
    checked = sum(item.get("checked", 0) for item in chunk_results)
    result = {
        "status": "finished",
        "chunks": len(chunk_results),
        "checked": checked,
        "failures": failures,
        "deactivated": deactivated,
    }
    logger.info("Stream probe wave finished: %s", result)
    return result


@shared_task(name="health.probe_active_streams")
def probe_active_streams_task() -> dict:
    """Dispatch chunked probes for all active stream URLs."""
    from django.core.cache import cache

    from health.stream_health import (
        PROBE_ACTIVE_LOCK_KEY,
        PROBE_LOCK_TTL,
        collect_active_channel_id_chunks,
    )

    if not cache.add(PROBE_ACTIVE_LOCK_KEY, "1", timeout=PROBE_LOCK_TTL):
        logger.info("Stream probe skipped: previous wave still running")
        return {"status": "skipped", "reason": "probe_in_progress"}

    timeout = settings.STREAM_PROBE_TIMEOUT
    chunk_size = settings.STREAM_PROBE_CHUNK_SIZE
    workers = settings.STREAM_PROBE_WORKERS
    match_chunks, tv_chunks = collect_active_channel_id_chunks(chunk_size=chunk_size)

    jobs = []
    for chunk in match_chunks:
        jobs.append(probe_match_channels_chunk_task.s(chunk, timeout, workers))
    for chunk in tv_chunks:
        jobs.append(probe_tv_channels_chunk_task.s(chunk, timeout, workers))

    if jobs:
        chord(group(jobs))(probe_wave_finished_task.s())
    else:
        cache.delete(PROBE_ACTIVE_LOCK_KEY)

    match_count = sum(len(chunk) for chunk in match_chunks)
    tv_count = sum(len(chunk) for chunk in tv_chunks)
    result = {
        "status": "dispatched",
        "chunks": len(jobs),
        "match_channels": match_count,
        "tv_channels": tv_count,
        "workers": workers,
        "health_failure_threshold": settings.CHANNEL_HEALTH_FAILURE_THRESHOLD,
    }
    logger.info("Stream probe dispatched: %s", result)
    return result


@shared_task(name="health.reactivate_match_channels_chunk")
def reactivate_match_channels_chunk_task(
    channel_ids: list[str],
    timeout: int,
    workers: int,
) -> dict:
    from health.stream_health import reactivate_match_channel_ids

    stats = reactivate_match_channel_ids(
        channel_ids,
        timeout=timeout,
        workers=workers,
    )
    return {"type": "match", **stats.__dict__}


@shared_task(name="health.reactivate_tv_channels_chunk")
def reactivate_tv_channels_chunk_task(
    channel_ids: list[str],
    timeout: int,
    workers: int,
) -> dict:
    from health.stream_health import reactivate_tv_channel_ids

    stats = reactivate_tv_channel_ids(
        channel_ids,
        timeout=timeout,
        workers=workers,
    )
    return {"type": "tv", **stats.__dict__}


@shared_task(name="health.reactivate_recovered_streams")
def reactivate_recovered_streams_task() -> dict:
    """Dispatch chunked reactivation probes for inactive channels."""
    from health.stream_health import collect_inactive_channel_id_chunks

    timeout = settings.STREAM_PROBE_TIMEOUT
    chunk_size = settings.STREAM_PROBE_CHUNK_SIZE
    workers = settings.STREAM_PROBE_WORKERS
    match_chunks, tv_chunks = collect_inactive_channel_id_chunks(chunk_size=chunk_size)

    jobs = []
    for chunk in match_chunks:
        jobs.append(reactivate_match_channels_chunk_task.s(chunk, timeout, workers))
    for chunk in tv_chunks:
        jobs.append(reactivate_tv_channels_chunk_task.s(chunk, timeout, workers))

    if jobs:
        group(jobs).apply_async()

    match_count = sum(len(chunk) for chunk in match_chunks)
    tv_count = sum(len(chunk) for chunk in tv_chunks)
    result = {
        "status": "dispatched",
        "chunks": len(jobs),
        "match_channels": match_count,
        "tv_channels": tv_count,
    }
    logger.info("Stream reactivation dispatched: %s", result)
    return result


@shared_task(name="health.run_all_maintenance")
def run_all_maintenance_task() -> dict:
    """Dispatch catalog sync, dead-link probe, and recovery reactivation."""
    return {
        "sync": sync_tv_catalog_task(),
        "probe": probe_active_streams_task(),
        "reactivate": reactivate_recovered_streams_task(),
    }
