"""Derive and sync match status from kickoff / end times."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from matches.cache import invalidate_match_caches
from matches.models import Match, MatchQuerySet, MatchStatus


def computed_status(
    *,
    starts_at: datetime,
    ends_at: datetime,
    now: datetime | None = None,
) -> str:
    """Return scheduled / live / ended from wall-clock times."""
    now = now or timezone.now()
    if now >= ends_at:
        return MatchStatus.ENDED
    if now >= starts_at - MatchQuerySet.live_lead():
        return MatchStatus.LIVE
    return MatchStatus.SCHEDULED


def sync_match_statuses() -> dict:
    """Align stored status with kickoff times (live from 2h before start)."""
    now = timezone.now()
    live_cutoff = now + MatchQuerySet.live_lead()

    live_count = (
        Match.objects.exclude(status=MatchStatus.LIVE)
        .filter(starts_at__lte=live_cutoff, ends_at__gt=now)
        .update(status=MatchStatus.LIVE)
    )

    ended_count = (
        Match.objects.exclude(status=MatchStatus.ENDED)
        .filter(ends_at__lte=now)
        .update(status=MatchStatus.ENDED)
    )

    scheduled_count = (
        Match.objects.exclude(status=MatchStatus.SCHEDULED)
        .filter(starts_at__gt=live_cutoff)
        .update(status=MatchStatus.SCHEDULED)
    )

    if live_count or ended_count or scheduled_count:
        invalidate_match_caches()

    return {
        "live": live_count,
        "ended": ended_count,
        "scheduled": scheduled_count,
    }
