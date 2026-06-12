from django.contrib import admin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html

from catalog.admin_actions import DeadLinkAdminActionsMixin
from catalog.models import CatalogChannel, CatalogSyncRun


class GroupedCatalogAutocompleteJsonView(AutocompleteJsonView):
    def get_queryset(self):
        qs = super().get_queryset()
        if self.model_admin is None:
            return qs
        return self.model_admin.grouped_autocomplete_queryset(qs)

    def serialize_result(self, obj, to_field_name):
        from catalog.grouping import siblings_for_group

        count = siblings_for_group(obj.group_key).count()
        parts = [obj.name]
        if obj.category:
            parts.append(obj.category)
        if obj.region:
            parts.append(obj.region)
        text = " · ".join(parts)
        if count > 1:
            text += f" ({count} sources)"
        return {"id": str(getattr(obj, to_field_name)), "text": text}


class CatalogChannelAdminBase(admin.ModelAdmin):
    search_fields = ("name", "stream_url", "category", "region")
    list_per_page = 50
    readonly_fields = (
        "external_key",
        "logo_preview_large",
        "failure_count",
        "deactivation_reason",
        "deactivated_at",
        "source_date",
        "last_seen_at",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Logo")
    def logo_preview(self, obj: CatalogChannel) -> str:
        if not obj.logo_url:
            return "—"
        return format_html(
            '<img src="{}" width="36" height="36" style="object-fit:contain;border-radius:4px" />',
            obj.logo_url,
        )

    @admin.display(description="Logo")
    def logo_preview_large(self, obj: CatalogChannel) -> str:
        if not obj.logo_url:
            return "—"
        return format_html(
            '<img src="{}" width="80" height="80" style="object-fit:contain;border-radius:8px" />',
            obj.logo_url,
        )

    @admin.display(description="Stream")
    def stream_link(self, obj: CatalogChannel) -> str:
        if not obj.stream_url:
            return "—"
        short = obj.stream_url if len(obj.stream_url) <= 48 else f"{obj.stream_url[:45]}…"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer" title="{}">{}</a>',
            obj.stream_url,
            obj.stream_url,
            short,
        )

    def get_urls(self):
        return [
            path(
                "details/<uuid:pk>/",
                self.admin_site.admin_view(self.channel_details),
                name="catalog_catalogchannel_details",
            ),
            *super().get_urls(),
        ]

    def grouped_autocomplete_queryset(self, queryset):
        from catalog.grouping import primary_channels_queryset

        return primary_channels_queryset(queryset.filter(is_active=True))

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request,
            queryset.filter(is_active=True),
            search_term,
        )
        return self.grouped_autocomplete_queryset(queryset), False

    def autocomplete_view(self, request):
        return GroupedCatalogAutocompleteJsonView.as_view(model_admin=self)(request)

    def channel_details(self, request, pk):
        from catalog.grouping import primary_for_catalog, siblings_for_group

        catalog = CatalogChannel.objects.get(pk=pk)
        primary = primary_for_catalog(catalog)
        siblings = list(siblings_for_group(primary.group_key))
        return JsonResponse(
            {
                "catalog_id": str(primary.pk),
                "name": primary.name,
                "logo_url": primary.logo_url,
                "stream_url": primary.stream_url,
                "language": primary.region,
                "category": primary.category,
                "source_count": len(siblings),
                "auto_sources": len(siblings) > 1,
            }
        )


@admin.register(CatalogChannel)
class CatalogChannelAdmin(DeadLinkAdminActionsMixin, CatalogChannelAdminBase):
    """Active TV channels shown in the app."""

    actions = ["mark_dead_link", "probe_and_deactivate_if_dead"]
    list_display = (
        "logo_preview",
        "name",
        "region",
        "category",
        "stream_link",
        "failure_count",
        "last_seen_at",
    )
    list_filter = ("region", "category")
    ordering = ("failure_count", "region", "category", "name")
    fieldsets = (
        (
            None,
            {
                "fields": ("name", "region", "category"),
                "description": "Inactive channels are reviewed under “Inactive TV channels (review)”.",
            },
        ),
        (
            "Stream",
            {
                "fields": (
                    "logo_url",
                    "logo_preview_large",
                    "stream_url",
                    "source_url",
                ),
            },
        ),
        (
            "Sync metadata",
            {
                "fields": (
                    "external_key",
                    "failure_count",
                    "source_date",
                    "last_seen_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_active=True)

    def has_add_permission(self, request):
        return False


class InactiveCatalogChannel(CatalogChannel):
    class Meta:
        proxy = True
        verbose_name = "inactive TV channel (review)"
        verbose_name_plural = "inactive TV channels (review)"


@admin.register(InactiveCatalogChannel)
class InactiveCatalogChannelAdmin(CatalogChannelAdminBase):
    """Channels removed from the app — verify stream, then reactivate manually."""

    list_display = (
        "logo_preview",
        "name",
        "region",
        "category",
        "failure_count",
        "deactivation_reason",
        "deactivated_at",
        "stream_link",
    )
    list_filter = ("deactivation_reason", "region", "category")
    ordering = ("-failure_count", "-deactivated_at", "name")
    actions = ["reactivate_channels"]
    fieldsets = (
        (
            "Review",
            {
                "fields": (
                    "name",
                    "region",
                    "category",
                    "failure_count",
                    "deactivation_reason",
                    "deactivated_at",
                ),
            },
        ),
        (
            "Stream",
            {
                "fields": (
                    "logo_url",
                    "logo_preview_large",
                    "stream_url",
                    "source_url",
                ),
            },
        ),
        (
            "Sync metadata",
            {
                "fields": (
                    "external_key",
                    "source_date",
                    "last_seen_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return CatalogChannel.objects.filter(is_active=False)

    def has_add_permission(self, request):
        return False

    @admin.action(description="Verify and reactivate (show in app again)")
    def reactivate_channels(self, request, queryset):
        for channel in queryset:
            channel.admin_reactivate()


@admin.register(CatalogSyncRun)
class CatalogSyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "started_at",
        "finished_at",
        "created_count",
        "updated_count",
        "skipped_count",
        "deactivated_count",
        "error_count",
    )
    readonly_fields = (
        "started_at",
        "finished_at",
        "regions",
        "created_count",
        "updated_count",
        "skipped_count",
        "deactivated_count",
        "error_count",
        "notes",
    )
