import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.deactivation import DeactivationReason
from catalog.field_limits import (
    CATALOG_CATEGORY_MAX_LENGTH,
    CATALOG_NAME_MAX_LENGTH,
    CATALOG_REGION_MAX_LENGTH,
    CATALOG_SOURCE_DATE_MAX_LENGTH,
)


def make_external_key(region: str, name: str, stream_url: str) -> str:
    raw = f"{region.strip().lower()}|{name.strip().lower()}|{stream_url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def make_group_key(name: str) -> str:
    raw = name.strip().casefold()
    return hashlib.sha256(raw.encode()).hexdigest()


class CatalogChannel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_key = models.CharField(max_length=64, unique=True, db_index=True)
    group_key = models.CharField(max_length=64, db_index=True, default="")
    region = models.CharField(max_length=CATALOG_REGION_MAX_LENGTH, db_index=True)
    category = models.CharField(
        max_length=CATALOG_CATEGORY_MAX_LENGTH, blank=True, db_index=True
    )
    name = models.CharField(max_length=CATALOG_NAME_MAX_LENGTH, db_index=True)
    logo_url = models.TextField(blank=True)
    stream_url = models.TextField()
    source_url = models.TextField(blank=True)
    source_date = models.CharField(max_length=CATALOG_SOURCE_DATE_MAX_LENGTH, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    failure_count = models.PositiveIntegerField(default=0)
    deactivation_reason = models.CharField(
        max_length=32,
        choices=DeactivationReason.choices,
        blank=True,
        db_index=True,
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TV channel"
        verbose_name_plural = "TV channels"
        ordering = ["region", "category", "name"]
        indexes = [
            models.Index(fields=["region", "is_active"]),
            models.Index(fields=["region", "category"]),
            models.Index(fields=["group_key", "is_active"]),
            models.Index(fields=["is_active", "-view_count"]),
        ]

    def __str__(self) -> str:
        return f"{self.region} / {self.name}"

    def save(self, *args, **kwargs):
        self.group_key = make_group_key(self.name)
        super().save(*args, **kwargs)

    def failure_threshold(self, source: str = "client_report") -> int:
        if source == "health_check":
            return getattr(settings, "CHANNEL_HEALTH_FAILURE_THRESHOLD", 3)
        return getattr(settings, "CHANNEL_FAILURE_THRESHOLD", 100)

    def record_success(self) -> None:
        if self.failure_count == 0:
            return
        self.failure_count = 0
        self.save(update_fields=["failure_count", "updated_at"])

    def deactivate(self, reason: str, *, notify: bool = True, source: str = "") -> None:
        if self.is_active:
            self.is_active = False
        self.deactivation_reason = reason
        self.deactivated_at = timezone.now()
        self.save(
            update_fields=[
                "is_active",
                "deactivation_reason",
                "deactivated_at",
                "updated_at",
            ]
        )
        from catalog.cache import invalidate_catalog_caches

        invalidate_catalog_caches(channel_id=self.pk)
        if notify and reason == DeactivationReason.USER_REPORTS:
            from catalog.notifications import notify_catalog_channel_deactivated

            notify_catalog_channel_deactivated(self, source=source or "client_report")

    def record_failure(self, source: str = "client_report") -> bool:
        """Increment failures; deactivate when threshold reached. Returns True if deactivated."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold(source):
            self.save(update_fields=["failure_count", "updated_at"])
            reason = (
                DeactivationReason.HEALTH_CHECK
                if source == "health_check"
                else DeactivationReason.USER_REPORTS
            )
            self.deactivate(
                reason,
                notify=reason == DeactivationReason.USER_REPORTS,
                source=source,
            )
            return True
        self.save(update_fields=["failure_count", "updated_at"])
        return False

    def admin_reactivate(self) -> None:
        """Re-enable after admin review. Only way back to the public catalog."""
        self.failure_count = 0
        self.is_active = True
        self.deactivation_reason = ""
        self.deactivated_at = None
        self.save(
            update_fields=[
                "failure_count",
                "is_active",
                "deactivation_reason",
                "deactivated_at",
                "updated_at",
            ]
        )
        from catalog.cache import invalidate_catalog_caches

        invalidate_catalog_caches(channel_id=self.pk)

    def reset_health(self) -> None:
        self.admin_reactivate()


class CatalogSyncRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    regions = models.JSONField(default=list)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    deactivated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(
        default=0,
        help_text="Upstream channels skipped because stream URL did not respond.",
    )
    error_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Sync {self.started_at:%Y-%m-%d %H:%M}"
