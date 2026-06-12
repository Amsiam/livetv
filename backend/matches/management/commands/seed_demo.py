from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import Channel, Match, MatchStatus


class Command(BaseCommand):
    help = "Seed demo matches and channels for local development."

    def handle(self, *args, **options):
        now = timezone.now()

        match, created = Match.objects.get_or_create(
            home_team="Team A",
            away_team="Team B",
            starts_at=now,
            defaults={
                "ends_at": now + timedelta(hours=2),
                "sport": "football",
                "status": MatchStatus.LIVE,
                "poster_url": "https://placehold.co/600x400/png",
                "sort_order": 10,
            },
        )

        if created:
            Channel.objects.bulk_create(
                [
                    Channel(
                        match=match,
                        name="Channel 1 HD",
                        language="en",
                        stream_url="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                        priority=2,
                    ),
                    Channel(
                        match=match,
                        name="Channel 2",
                        language="en",
                        stream_url="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                        priority=1,
                    ),
                ]
            )

        scheduled_start = now + timedelta(hours=2)
        Match.objects.get_or_create(
            home_team="Team C",
            away_team="Team D",
            starts_at=scheduled_start,
            defaults={
                "ends_at": scheduled_start + timedelta(hours=2),
                "sport": "football",
                "status": MatchStatus.SCHEDULED,
                "sort_order": 5,
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
