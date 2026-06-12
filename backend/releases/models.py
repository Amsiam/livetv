from django.db import models


class AppPlatform(models.TextChoices):
    ANDROID = "android", "Android"


class AppRelease(models.Model):
    platform = models.CharField(
        max_length=20,
        choices=AppPlatform.choices,
        default=AppPlatform.ANDROID,
    )
    version_name = models.CharField(
        max_length=32,
        help_text="Human-readable version, e.g. 1.0.1",
    )
    build_number = models.PositiveIntegerField(
        help_text="Must match Flutter pubspec build number (1.0.0+N).",
    )
    min_build_number = models.PositiveIntegerField(
        default=1,
        help_text="Users below this build are forced to update.",
    )
    apk_file = models.FileField(
        upload_to="releases/",
        blank=True,
        help_text="Uploaded APK; download URL is filled automatically on save.",
    )
    download_url = models.URLField(
        max_length=2048,
        blank=True,
        help_text="Public HTTPS link served to the app (auto-set when APK file is uploaded).",
    )
    force_update = models.BooleanField(
        default=False,
        help_text="When enabled, any user below build_number must update.",
    )
    release_notes = models.TextField(blank=True)
    is_published = models.BooleanField(
        default=True,
        help_text="Only the latest published row per platform is served to the app.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-build_number", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["platform", "build_number"],
                name="releases_unique_platform_build",
            )
        ]

    def __str__(self) -> str:
        return f"{self.platform} {self.version_name} ({self.build_number})"

    def resolved_download_url(self) -> str:
        """URL served to the app — always the value stored at publish time."""
        if self.download_url:
            return self.download_url
        if self.apk_file:
            from releases.media_urls import public_media_url

            return public_media_url(self.apk_file.name)
        return ""

    def save(self, *args, **kwargs):
        new_apk = bool(
            self.apk_file and not getattr(self.apk_file, "_committed", True)
        )

        super().save(*args, **kwargs)

        if self.apk_file:
            from releases.apk_files import store_canonical_apk
            from releases.media_urls import public_media_url

            if new_apk:
                store_canonical_apk(self)

            download_url = public_media_url(self.apk_file.name)
            if self.download_url != download_url:
                type(self).objects.filter(pk=self.pk).update(download_url=download_url)
                self.download_url = download_url

        from releases.cache import invalidate_latest_release_cache

        invalidate_latest_release_cache(self.platform)

    def delete(self, *args, **kwargs):
        platform = self.platform
        super().delete(*args, **kwargs)
        from releases.cache import invalidate_latest_release_cache

        invalidate_latest_release_cache(platform)
