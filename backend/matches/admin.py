from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from catalog.admin_actions import DeadLinkAdminActionsMixin
from matches.models import Channel, Match, MatchStatus


class ChannelInline(admin.TabularInline):
    model = Channel
    extra = 1
    verbose_name = "match channel"
    verbose_name_plural = (
        "match channels — pick a grouped TV channel or leave catalog empty and fill manually"
    )
    fields = (
        "catalog_channel",
        "name",
        "language",
        "logo_url",
        "stream_url",
        "follow_catalog_stream",
        "priority",
        "is_active",
    )
    ordering = ("-priority", "name")
    autocomplete_fields = ("catalog_channel",)
    readonly_fields = ("follow_catalog_stream", "url_updated_at")

    class Media:
        js = ("matches/admin/channel_catalog_fill.js",)


class MatchResource(resources.ModelResource):
    class Meta:
        model = Match
        fields = (
            "id",
            "title",
            "sport",
            "home_team",
            "away_team",
            "starts_at",
            "ends_at",
            "status",
            "poster_url",
            "match_number",
            "tournament_group",
            "round",
            "venue",
            "city",
            "sort_order",
        )


@admin.register(Match)
class MatchAdmin(ImportExportModelAdmin):
    resource_class = MatchResource
    list_display = (
        "display_title",
        "sport",
        "match_number",
        "round",
        "status",
        "starts_at",
        "ends_at",
        "sort_order",
    )
    list_filter = ("status", "sport", "round")
    search_fields = ("title", "home_team", "away_team")
    inlines = [ChannelInline]
    actions = ["mark_live", "mark_ended"]

    class Media:
        js = ("matches/admin/channel_catalog_fill.js",)

    @admin.display(description="Title")
    def display_title(self, obj: Match) -> str:
        return obj.display_title

    @admin.action(description="Mark selected as live")
    def mark_live(self, request, queryset):
        queryset.update(status=MatchStatus.LIVE)

    @admin.action(description="Mark selected as ended")
    def mark_ended(self, request, queryset):
        queryset.update(status=MatchStatus.ENDED)


class ChannelAdminBase(admin.ModelAdmin):
    search_fields = ("name", "match__home_team", "match__away_team", "stream_url")
    list_select_related = ("match", "catalog_channel")
    list_per_page = 50
    autocomplete_fields = ("catalog_channel",)
    readonly_fields = (
        "follow_catalog_stream",
        "failure_count",
        "deactivation_reason",
        "deactivated_at",
        "url_updated_at",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Stream")
    def stream_link(self, obj: Channel) -> str:
        if not obj.stream_url:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">Open</a>',
            obj.stream_url,
        )


@admin.register(Channel)
class ChannelAdmin(DeadLinkAdminActionsMixin, ChannelAdminBase):
    list_display = (
        "name",
        "match",
        "catalog_channel",
        "stream_link",
        "follow_catalog_stream",
        "language",
        "priority",
        "failure_count",
        "url_updated_at",
    )
    list_filter = ("language", "follow_catalog_stream", "match__status")
    actions = ["mark_dead_link", "probe_and_deactivate_if_dead"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "match",
                    "catalog_channel",
                    "name",
                    "language",
                    "logo_url",
                    "stream_url",
                    "follow_catalog_stream",
                    "priority",
                ),
                "description": (
                    "Pick a grouped TV channel (search by name) to auto-fill everything "
                    "and expose all of its sources in the app. "
                    "Leave catalog empty to enter a manual stream instead. "
                    "Inactive match channels are reviewed under “Inactive match channels (review)”."
                ),
            },
        ),
        (
            "Health",
            {
                "fields": (
                    "failure_count",
                    "url_updated_at",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    class Media:
        js = ("matches/admin/channel_catalog_fill.js",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_active=True)

class InactiveMatchChannel(Channel):
    class Meta:
        proxy = True
        verbose_name = "inactive match channel (review)"
        verbose_name_plural = "inactive match channels (review)"


@admin.register(InactiveMatchChannel)
class InactiveMatchChannelAdmin(ChannelAdminBase):
    list_display = (
        "name",
        "match",
        "failure_count",
        "deactivation_reason",
        "deactivated_at",
        "stream_link",
        "language",
        "priority",
    )
    list_filter = ("deactivation_reason", "language", "match__status")
    ordering = ("-deactivated_at", "name")
    actions = ["reactivate_channels"]
    fieldsets = (
        (
            "Review",
            {
                "fields": (
                    "match",
                    "name",
                    "language",
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
                    "catalog_channel",
                    "logo_url",
                    "stream_url",
                    "follow_catalog_stream",
                    "priority",
                ),
            },
        ),
        (
            "Health",
            {
                "fields": ("url_updated_at", "created_at", "updated_at"),
            },
        ),
    )

    class Media:
        js = ("matches/admin/channel_catalog_fill.js",)

    def get_queryset(self, request):
        return Channel.objects.filter(is_active=False)

    def has_add_permission(self, request):
        return False

    @admin.action(description="Verify and reactivate (show in app again)")
    def reactivate_channels(self, request, queryset):
        for channel in queryset:
            channel.admin_reactivate()
