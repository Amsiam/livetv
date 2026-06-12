from collections import defaultdict
from urllib.parse import urlparse

from catalog.grouping import siblings_for_group, source_label
from catalog.models import CatalogChannel
from matches.models import Channel


def name_group_key(name: str) -> str:
    return name.strip().casefold()


def match_channel_group_key(channel: Channel) -> str:
    if channel.catalog_channel_id and channel.catalog_channel.group_key:
        return f"catalog:{channel.catalog_channel.group_key}"
    return f"name:{name_group_key(channel.name)}"


def _source_host(stream_url: str) -> str:
    try:
        return urlparse(stream_url).hostname or ""
    except ValueError:
        return ""


def primary_channel(channels: list[Channel]) -> Channel:
    return sorted(
        channels,
        key=lambda ch: (-ch.priority, ch.failure_count, -ch.updated_at.timestamp()),
    )[0]


def group_channels_by_name(
    channels: list[Channel],
) -> tuple[list[Channel], dict[str, list[Channel]]]:
    grouped: dict[str, list[Channel]] = defaultdict(list)
    for channel in channels:
        grouped[match_channel_group_key(channel)].append(channel)

    siblings_by_group = dict(grouped)
    primaries = [primary_channel(group) for group in grouped.values()]
    primaries.sort(key=lambda ch: (-ch.priority, match_channel_group_key(ch)))
    return primaries, siblings_by_group


def _catalog_for_siblings(channel: Channel, match_siblings: list[Channel]) -> CatalogChannel | None:
    if channel.catalog_channel_id:
        return channel.catalog_channel
    for sibling in match_siblings:
        if sibling.catalog_channel_id:
            return sibling.catalog_channel
    return None


def collect_match_sources(channel: Channel, match_siblings: list[Channel]) -> list[dict]:
    seen_urls: set[str] = set()
    entries: list[tuple[str, str, str]] = []

    ordered_match_rows = sorted(
        match_siblings,
        key=lambda ch: (ch.failure_count, -ch.priority, -ch.updated_at.timestamp()),
    )
    for row in ordered_match_rows:
        url = (row.stream_url or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        entries.append((str(row.id), url, "match"))

    catalog = _catalog_for_siblings(channel, match_siblings)
    if catalog is not None:
        for cat in siblings_for_group(catalog.group_key):
            url = (cat.stream_url or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            entries.append((str(cat.id), url, "catalog"))

    return [
        {
            "id": source_id,
            "stream_url": stream_url,
            "label": source_label(index),
            "host": _source_host(stream_url),
            "kind": kind,
        }
        for index, (source_id, stream_url, kind) in enumerate(entries, start=1)
    ]


def serialize_match_sources(channels: list[Channel]) -> list[dict]:
    if not channels:
        return []
    primary = primary_channel(channels)
    return collect_match_sources(primary, channels)
