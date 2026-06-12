from django import forms

from releases.apk_files import clear_stale_apk_files
from releases.models import AppRelease


class AppReleaseAdminForm(forms.ModelForm):
    """Admin upload form — version/build must be set before the APK is stored."""

    class Meta:
        model = AppRelease
        fields = (
            "platform",
            "version_name",
            "build_number",
            "min_build_number",
            "apk_file",
            "force_update",
            "release_notes",
            "is_published",
        )

    def clean(self):
        cleaned = super().clean()
        apk = cleaned.get("apk_file")
        if apk and not getattr(apk, "_committed", True):
            if not cleaned.get("version_name"):
                self.add_error(
                    "version_name",
                    "Enter the version name before uploading the APK.",
                )
            if cleaned.get("build_number") is None:
                self.add_error(
                    "build_number",
                    "Enter the build number before uploading the APK.",
                )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_apk = bool(
            instance.apk_file and not getattr(instance.apk_file, "_committed", True)
        )
        if new_apk:
            clear_stale_apk_files(instance)
        if commit:
            instance.save()
            instance.sync_download_url()
        return instance
