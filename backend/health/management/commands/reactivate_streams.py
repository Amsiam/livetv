from django.conf import settings
from django.core.management.base import BaseCommand

from health.stream_health import reactivate_recovered_streams


class Command(BaseCommand):
    help = "Probe inactive channels and reactivate those with a live stream URL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=None,
            help="HTTP timeout in seconds for each probe.",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"] or settings.STREAM_PROBE_TIMEOUT
        result = reactivate_recovered_streams(timeout=timeout)

        for label, stats in (
            ("Match channels", result.match_channels),
            ("TV channels", result.tv_channels),
        ):
            self.stdout.write(
                f"{label}: checked {stats.checked}, reactivated {stats.reactivated}"
            )

        total = result.match_channels.reactivated + result.tv_channels.reactivated
        self.stdout.write(
            self.style.SUCCESS(f"Done — {total} channel(s) reactivated.")
        )
