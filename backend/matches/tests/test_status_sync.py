from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from matches.models import Match, MatchStatus
from matches.status_sync import computed_status, sync_match_statuses


class MatchStatusSyncTests(TestCase):
    def test_computed_status_scheduled_outside_live_window(self):
        now = timezone.now()
        starts = now + timedelta(days=1)
        self.assertEqual(
            computed_status(starts_at=starts, ends_at=starts + timedelta(hours=2), now=now),
            MatchStatus.SCHEDULED,
        )

    def test_computed_status_live_two_hours_before_kickoff(self):
        now = timezone.now()
        starts = now + timedelta(hours=2)
        self.assertEqual(
            computed_status(starts_at=starts, ends_at=starts + timedelta(hours=2), now=now),
            MatchStatus.LIVE,
        )

    def test_computed_status_ended_after_finish(self):
        now = timezone.now()
        starts = now - timedelta(hours=3)
        ends = now - timedelta(minutes=1)
        self.assertEqual(
            computed_status(starts_at=starts, ends_at=ends, now=now),
            MatchStatus.ENDED,
        )

    def test_sync_match_statuses_updates_rows(self):
        now = timezone.now()
        live_match = Match.objects.create(
            sport="football",
            home_team="A",
            away_team="B",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=3),
            status=MatchStatus.SCHEDULED,
        )
        ended_match = Match.objects.create(
            sport="football",
            home_team="C",
            away_team="D",
            starts_at=now - timedelta(hours=4),
            ends_at=now - timedelta(minutes=5),
            status=MatchStatus.LIVE,
        )
        future_match = Match.objects.create(
            sport="football",
            home_team="E",
            away_team="F",
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=2),
            status=MatchStatus.LIVE,
        )

        result = sync_match_statuses()

        live_match.refresh_from_db()
        ended_match.refresh_from_db()
        future_match.refresh_from_db()

        self.assertEqual(result["live"], 1)
        self.assertEqual(result["ended"], 1)
        self.assertEqual(result["scheduled"], 1)
        self.assertEqual(live_match.status, MatchStatus.LIVE)
        self.assertEqual(ended_match.status, MatchStatus.ENDED)
        self.assertEqual(future_match.status, MatchStatus.SCHEDULED)
