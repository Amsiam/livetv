import argparse

from django.core.management.base import BaseCommand

from catalog.sync import resolve_regions, sync_regions


class Command(BaseCommand):
    help = "Sync TV channel catalog from LiveTVCollector GitHub repository."

    def add_arguments(self, parser):
        parser.add_argument(
            "--regions",
            type=str,
            help="Comma-separated regions (e.g. Bangladesh,India). Overrides LIVETV_COLLECTOR_REGIONS.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Sync all regions from index.json (large; may take several minutes).",
        )
        parser.add_argument(
            "--keep-missing",
            action="store_true",
            help="Do not deactivate channels missing from the latest upstream file.",
        )
        parser.add_argument(
            "--probe",
            action="store_true",
            help="Probe stream URLs before save (slow). Default: save all and rely on user feedback.",
        )
        parser.add_argument(
            "--skip-probe",
            action="store_true",
            help=argparse.SUPPRESS,
        )

    def handle(self, *args, **options):
        explicit = None
        if options["regions"]:
            explicit = [r.strip() for r in options["regions"].split(",") if r.strip()]

        regions = resolve_regions(explicit=explicit, sync_all=options["all"])
        deactivate_missing = not options["keep_missing"]
        verify_streams = options["probe"] and not options["skip_probe"]

        self.stdout.write(f"Syncing regions: {', '.join(regions)}")
        if verify_streams:
            self.stdout.write("Probing stream URLs before save")
        else:
            self.stdout.write(
                "Saving upstream URLs without probe (dead streams reported by app users)"
            )
        run = sync_regions(
            regions,
            deactivate_missing=deactivate_missing,
            verify_streams=verify_streams,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — created {run.created_count}, updated {run.updated_count}, "
                f"skipped {run.skipped_count}, deactivated {run.deactivated_count}, "
                f"errors {run.error_count}"
            )
        )
