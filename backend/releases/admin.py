from django.contrib import admin

from releases.models import AppRelease


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "platform",
        "version_name",
        "build_number",
        "min_build_number",
        "force_update",
        "is_published",
        "updated_at",
    )
    list_filter = ("platform", "is_published", "force_update")
    search_fields = ("version_name", "download_url")
    ordering = ("-build_number",)
    readonly_fields = ("download_url",)
    fields = (
        "platform",
        "version_name",
        "build_number",
        "min_build_number",
        "apk_file",
        "download_url",
        "force_update",
        "release_notes",
        "is_published",
    )
