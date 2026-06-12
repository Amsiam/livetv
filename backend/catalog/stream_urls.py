"""Stream URL format helpers for the live TV catalog."""

from __future__ import annotations

from urllib.parse import urlparse


def is_hls_stream_url(url: str) -> bool:
    """Return True when the URL points at an HLS playlist (m3u8)."""
    cleaned = (url or "").strip()
    if not cleaned.lower().startswith(("http://", "https://")):
        return False

    parsed = urlparse(cleaned)
    path = (parsed.path or "").lower()
    if ".m3u8" in path:
        return True

    combined = f"{parsed.query or ''}{parsed.fragment or ''}".lower()
    return "m3u8" in combined
