from django.core.management.base import BaseCommand, CommandError

from matches.fifa_schedule import import_fifa_world_cup_2026_schedule


class Command(BaseCommand):
    help = (
        "Import FIFA World Cup 2026 schedule (M1–M104) and link all "
        "active FIFA World Cup 2026 catalog TV channels to every match."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing FIFA World Cup 2026 matches before import.",
        )

    def handle(self, *args, **options):
        try:
            result = import_fifa_world_cup_2026_schedule(replace=options["replace"])
        except LookupError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"FIFA schedule import complete: "
                f"{result['matches_created']} created, "
                f"{result['matches_updated']} updated, "
                f"{result['total_matches']} total — "
                f"TV: {', '.join(result['tv_channels'])}"
            )
        )
