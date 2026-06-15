from __future__ import annotations

from catalog.field_limits import (
    CATALOG_CATEGORY_MAX_LENGTH,
    CATALOG_NAME_MAX_LENGTH,
    CATALOG_REGION_MAX_LENGTH,
    CATALOG_SOURCE_DATE_MAX_LENGTH,
)

# Display text only — stream/logo/source URLs must stay intact for playback.
_TRUNCATABLE_FIELDS: tuple[tuple[str, int], ...] = (
    ("region", CATALOG_REGION_MAX_LENGTH),
    ("category", CATALOG_CATEGORY_MAX_LENGTH),
    ("name", CATALOG_NAME_MAX_LENGTH),
    ("source_date", CATALOG_SOURCE_DATE_MAX_LENGTH),
)


def truncate_text(value: str, max_length: int) -> str:
    text = (value or "").strip()
    if len(text) <= max_length:
        return text
    return text[:max_length]


def fit_catalog_entry(entry: dict) -> tuple[dict, list[str]]:
    """Trim display text to model limits. URLs are left unchanged."""
    result = dict(entry)
    truncated: list[str] = []

    for field, max_length in _TRUNCATABLE_FIELDS:
        original = (result.get(field) or "").strip()
        fitted = truncate_text(original, max_length)
        if len(original) > max_length:
            truncated.append(field)
        result[field] = fitted

    return result, truncated
