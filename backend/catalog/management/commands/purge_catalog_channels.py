from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.cache import invalidate_catalog_caches
from catalog.models import CatalogChannel

DEFAULT_KEEP_REGIONS = ("Bangladesh", "India", "Pakistan")


class Command(BaseCommand):
    help = (
        "Delete TV catalog channels by region. "
        "Use --keep-only to remove every region except the listed ones."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--regions",
            type=str,
            help="Comma-separated regions to delete (e.g. Bahrain,Saudi Arabia).",
        )
        group.add_argument(
            "--keep-only",
            type=str,
            nargs="?",
            const=",".join(DEFAULT_KEEP_REGIONS),
            default=None,
            help=(
                "Delete all channels NOT in these regions. "
                f"Default when flag is passed alone: {', '.join(DEFAULT_KEEP_REGIONS)}."
            ),
        )

    def handle(self, *args, **options):
        if options["regions"]:
            regions = [r.strip() for r in options["regions"].split(",") if r.strip()]
            if not regions:
                raise CommandError("Provide at least one region with --regions.")
            qs = CatalogChannel.objects.filter(region__in=regions)
            mode = f"regions {', '.join(regions)}"
        else:
            keep = options["keep_only"]
            if keep is None:
                raise CommandError("Use --regions or --keep-only.")
            keep_regions = [r.strip() for r in keep.split(",") if r.strip()]
            if not keep_regions:
                raise CommandError("Provide at least one region to keep.")
            qs = CatalogChannel.objects.exclude(region__in=keep_regions)
            mode = f"all except {', '.join(keep_regions)}"

        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.WARNING(f"No catalog channels matched ({mode})."))
            return

        self.stdout.write(f"Deleting {count} catalog channel(s) — {mode}")
        with transaction.atomic():
            deleted, breakdown = qs.delete()
        invalidate_catalog_caches()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done — deleted {deleted} row(s) "
                f"(catalog channels: {breakdown.get('catalog.CatalogChannel', 0)})."
            )
        )
