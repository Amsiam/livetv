from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings

from health.stream_probe import probe_stream_url


def probe_settings() -> tuple[bool, int, int]:
    enabled = getattr(settings, "CATALOG_SYNC_PROBE_STREAMS", True)
    timeout = int(getattr(settings, "CATALOG_SYNC_PROBE_TIMEOUT", 5))
    workers = int(getattr(settings, "CATALOG_SYNC_PROBE_WORKERS", 20))
    return enabled, timeout, workers


def filter_reachable_entries(
    entries: list[dict],
    *,
    timeout: int | None = None,
    workers: int | None = None,
) -> tuple[list[dict], int]:
    """Keep only entries whose stream_url responds. Returns (alive, skipped_count)."""
    if not entries:
        return [], 0

    _, default_timeout, default_workers = probe_settings()
    timeout = default_timeout if timeout is None else timeout
    workers = default_workers if workers is None else workers
    workers = max(1, min(workers, len(entries)))

    alive: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(probe_stream_url, entry["stream_url"], timeout): entry
            for entry in entries
        }
        for future in as_completed(futures):
            entry = futures[future]
            try:
                if future.result():
                    alive.append(entry)
            except Exception:
                pass

    return alive, len(entries) - len(alive)
