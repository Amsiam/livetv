"""Import FIFA World Cup 2026 schedule into matches + TV channels."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from catalog.models import CatalogChannel
from matches.data.fifa_world_cup_2026_schedule import (
    FIFA_PREFERRED_CHANNEL_NAMES,
    FIFA_WORLD_CUP_2026_CATEGORY,
    FIFA_WORLD_CUP_2026_SPORT,
    SCHEDULE,
)
from matches.models import Channel, Match
from matches.status_sync import computed_status


MATCH_DURATION = timedelta(hours=2, minutes=15)


def _aware(dt):
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.utc)
    return dt


def build_match_title(entry: dict) -> str:
    number = entry["match_number"]
    home = entry["home_team"]
    away = entry["away_team"]
    group = entry.get("group")
    round_name = entry["round"]
    prefix = f"M{number}"
    if group:
        prefix = f"{prefix} · Group {group}"
    else:
        prefix = f"{prefix} · {round_name}"
    return f"{prefix}: {home} vs {away}"


def resolve_fifa_channels() -> list[tuple[str, CatalogChannel, int]]:
    """Return (label, catalog_channel, priority) for FIFA World Cup TV sources.

    Includes all active catalog channels in ``FIFA_WORLD_CUP_2026_CATEGORY``,
    with preferred names first. Preferred names fall back to any active catalog
    row when missing from the category (e.g. plain ``T Sports HD ``).
    """
    category_rows = list(
        CatalogChannel.objects.filter( 
            is_active=True,
            category=FIFA_WORLD_CUP_2026_CATEGORY,
        ).order_by("name")
    )
    by_name_in_category = {row.name: row for row in category_rows}

    resolved: list[tuple[str, CatalogChannel, int]] = []
    seen_ids: set = set()
    priority = len(category_rows) + len(FIFA_PREFERRED_CHANNEL_NAMES)

    for preferred_name in FIFA_PREFERRED_CHANNEL_NAMES:
        channel = by_name_in_category.get(preferred_name)
        if channel is None:
            channel = (
                CatalogChannel.objects.filter(is_active=True, name=preferred_name)
                .order_by("-updated_at")
                .first()
            )
        if channel is None or channel.id in seen_ids:
            continue
        resolved.append((preferred_name, channel, priority))
        seen_ids.add(channel.id)
        priority -= 1

    for channel in category_rows:
        if channel.id in seen_ids:
            continue
        resolved.append((channel.name, channel, priority))
        seen_ids.add(channel.id)
        priority -= 1

    if not resolved:
        raise LookupError(
            f"No active catalog channels found for category "
            f"{FIFA_WORLD_CUP_2026_CATEGORY!r} "
            f"(preferred: {', '.join(FIFA_PREFERRED_CHANNEL_NAMES)})"
        )

    return resolved


def import_fifa_world_cup_2026_schedule(*, replace: bool = False) -> dict:
    """Create or update all 104 FIFA matches and attach World Cup TV sources."""
    tv_channels = resolve_fifa_channels()
    allowed_catalog_ids = {catalog.id for _, catalog, _ in tv_channels}
    now = timezone.now()
    created = 0
    updated = 0
    channels_linked = 0
    channels_removed = 0

    with transaction.atomic():
        if replace:
            Match.objects.filter(sport=FIFA_WORLD_CUP_2026_SPORT).delete()

        for entry in SCHEDULE:
            starts_at = _aware(parse_datetime(entry["utc_date"]))
            ends_at = starts_at + MATCH_DURATION
            defaults = {
                "title": build_match_title(entry),
                "home_team": entry["home_team"],
                "away_team": entry["away_team"],
                "starts_at": starts_at,
                "ends_at": ends_at,
                "status": computed_status(
                    starts_at=starts_at,
                    ends_at=ends_at,
                    now=now,
                ),
                "tournament_group": entry.get("group") or "",
                "round": entry["round"],
                "venue": entry["venue"],
                "city": entry["city"],
                "sort_order": entry["match_number"],
            }

            match, was_created = Match.objects.update_or_create(
                sport=FIFA_WORLD_CUP_2026_SPORT,
                match_number=entry["match_number"],
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

            removed, _ = (
                match.channels.exclude(catalog_channel_id__in=allowed_catalog_ids)
                .delete()
            )
            channels_removed += removed

            for label, catalog, channel_priority in tv_channels:
                channel, ch_created = Channel.objects.update_or_create(
                    match=match,
                    catalog_channel=catalog,
                    defaults={
                        "name": label,
                        "priority": channel_priority,
                        "is_active": True,
                    },
                )
                channel.save()
                if ch_created:
                    channels_linked += 1

    from matches.cache import invalidate_match_caches

    invalidate_match_caches()

    return {
        "sport": FIFA_WORLD_CUP_2026_SPORT,
        "category": FIFA_WORLD_CUP_2026_CATEGORY,
        "matches_created": created,
        "matches_updated": updated,
        "channels_linked": channels_linked,
        "channels_removed": channels_removed,
        "total_matches": len(SCHEDULE),
        "tv_channels": [label for label, _, _ in tv_channels],
    }
