from django.contrib import admin
from django.utils.html import format_html

from releases.forms import AppReleaseAdminForm
from releases.models import AppRelease


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    form = AppReleaseAdminForm
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
    readonly_fields = ("download_url_display",)
    fields = (
        "platform",
        "version_name",
        "build_number",
        "min_build_number",
        "apk_file",
        "download_url_display",
        "force_update",
        "release_notes",
        "is_published",
    )

    @admin.display(description="Download url")
    def download_url_display(self, obj: AppRelease) -> str:
        if not obj.pk:
            return "Save the release to generate the download URL."
        url = obj.resolved_download_url()
        if not url:
            return "Upload an APK and save."
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            url,
            url,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.refresh_from_db()
        obj.sync_download_url()
