"""Small helpers for consistent structured log context."""

from __future__ import annotations

import logging


def log_extra(**fields) -> dict[str, object]:
    """Return kwargs for ``logger.*(..., extra=log_extra(...))``.

    Renames keys that collide with :class:`logging.LogRecord` attributes
    (e.g. ``created`` → ``stat_created``).
    """
    reserved = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
    result: dict[str, object] = {}
    for key, value in fields.items():
        if value is None:
            continue
        safe_key = key if key not in reserved else f"stat_{key}"
        result[safe_key] = value
    return result


def sample_channel_fields(entry: dict) -> dict[str, object]:
    """Safe summary of a catalog entry for error logs (no full URLs)."""
    name = (entry.get("name") or "")[:120]
    stream_url = entry.get("stream_url") or ""
    return {
        "channel_name": name,
        "stream_url_len": len(stream_url),
        "category_len": len(entry.get("category") or ""),
        "logo_url_len": len(entry.get("logo_url") or ""),
    }
