from django.conf import settings
from django.core.management.base import BaseCommand

from health.stream_health import probe_active_streams


class Command(BaseCommand):
    help = (
        "Probe active match and TV channel stream URLs; "
        "deactivate after consecutive failures."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=None,
            help="HTTP timeout in seconds for each probe.",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"] or settings.STREAM_PROBE_TIMEOUT
        result = probe_active_streams(timeout=timeout)

        for label, stats in (
            ("Match channels", result.match_channels),
            ("TV channels", result.tv_channels),
        ):
            self.stdout.write(
                f"{label}: checked {stats.checked}, "
                f"failures {stats.failures}, deactivated {stats.deactivated}"
            )

        total_deactivated = (
            result.match_channels.deactivated + result.tv_channels.deactivated
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {total_deactivated} channel(s) deactivated."
            )
        )
