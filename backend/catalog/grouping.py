from collections import defaultdict
from urllib.parse import urlparse

from django.db import connection
from django.db.models import Case, F, IntegerField, QuerySet, Sum, When, Window
from django.db.models.functions import RowNumber

from catalog.models import CatalogChannel
from catalog.view_counts import batch_effective_view_counts


def source_label(index: int) -> str:
    return f"Source {index}"


def source_host(stream_url: str) -> str:
    try:
        host = urlparse(stream_url).hostname or ""
    except ValueError:
        host = ""
    return host


def serialize_sources(channels: list[CatalogChannel]) -> list[dict]:
    ordered = sorted(
        channels,
        key=lambda ch: (ch.failure_count, -ch.updated_at.timestamp()),
    )
    return [
        {
            "id": str(channel.id),
            "stream_url": channel.stream_url,
            "label": source_label(index),
            "host": source_host(channel.stream_url),
        }
        for index, channel in enumerate(ordered, start=1)
    ]


def siblings_for_group(group_key: str) -> QuerySet[CatalogChannel]:
    return CatalogChannel.objects.filter(
        group_key=group_key,
        is_active=True,
    ).order_by("failure_count", "-updated_at")


def siblings_by_group_keys(group_keys: list[str]) -> dict[str, list[CatalogChannel]]:
    if not group_keys:
        return {}
    rows = CatalogChannel.objects.filter(
        group_key__in=group_keys,
        is_active=True,
    ).order_by("group_key", "failure_count", "-updated_at")
    grouped: dict[str, list[CatalogChannel]] = defaultdict(list)
    for row in rows:
        grouped[row.group_key].append(row)
    return grouped


def primary_for_group(group_key: str) -> CatalogChannel | None:
    if not group_key:
        return None
    return primary_channels_queryset(
        CatalogChannel.objects.filter(group_key=group_key, is_active=True)
    ).first()


def primary_for_catalog(channel: CatalogChannel) -> CatalogChannel:
    if not channel.group_key:
        return channel
    return primary_for_group(channel.group_key) or channel


def _preserve_id_order(model, ordered_ids: list) -> QuerySet[CatalogChannel]:
    if not ordered_ids:
        return model.objects.none()
    whens = [When(pk=pk, then=position) for position, pk in enumerate(ordered_ids)]
    return model.objects.filter(pk__in=ordered_ids).order_by(
        Case(*whens, output_field=IntegerField())
    )


def order_channels_by_popularity(
    queryset: QuerySet[CatalogChannel],
    *,
    grouped: bool,
) -> QuerySet[CatalogChannel]:
    rows = list(
        queryset.values("id", "group_key", "view_count", "region", "category", "name")
    )
    if not rows:
        return queryset.none()

    effective = batch_effective_view_counts(
        {str(row["id"]): row["view_count"] for row in rows}
    )

    if grouped:
        group_keys = {row["group_key"] for row in rows}
        siblings = CatalogChannel.objects.filter(
            is_active=True,
            group_key__in=group_keys,
        ).values("id", "group_key", "view_count")
        sibling_effective = batch_effective_view_counts(
            {str(row["id"]): row["view_count"] for row in siblings}
        )
        group_totals: dict[str, int] = defaultdict(int)
        for row in siblings:
            group_totals[row["group_key"]] += sibling_effective[str(row["id"])]

        def sort_key(row: dict) -> tuple:
            return (
                -group_totals[row["group_key"]],
                row["region"],
                row["category"],
                row["name"],
            )
    else:

        def sort_key(row: dict) -> tuple:
            return (
                -effective[str(row["id"])],
                row["region"],
                row["category"],
                row["name"],
            )

    sorted_ids = [row["id"] for row in sorted(rows, key=sort_key)]
    return _preserve_id_order(queryset.model, sorted_ids)


def primary_channels_queryset(queryset: QuerySet[CatalogChannel]) -> QuerySet[CatalogChannel]:
    """One primary row per group_key, ordered by total group views (SQL — paginate-friendly)."""
    if connection.vendor == "postgresql":
        return (
            queryset.annotate(
                group_view_total=Window(
                    expression=Sum("view_count"),
                    partition_by=[F("group_key")],
                ),
                row_num=Window(
                    expression=RowNumber(),
                    partition_by=[F("group_key")],
                    order_by=[F("failure_count").asc(), F("updated_at").desc()],
                ),
            )
            .filter(row_num=1)
            .order_by("-group_view_total", "region", "category", "name")
        )

    ordered = list(queryset.order_by("group_key", "failure_count", "-updated_at"))
    seen: set[str] = set()
    primary_ids: list = []
    for channel in ordered:
        if channel.group_key in seen:
            continue
        seen.add(channel.group_key)
        primary_ids.append(channel.id)
    primaries = queryset.model.objects.filter(id__in=primary_ids)
    return order_channels_by_popularity(primaries, grouped=True)
