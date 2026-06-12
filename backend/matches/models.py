import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from catalog.deactivation import DeactivationReason


class MatchStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    LIVE = "live", "Live"
    ENDED = "ended", "Ended"


class MatchQuerySet(models.QuerySet):
    VISIBILITY_DAYS_BEFORE_START = 2
    VISIBILITY_EXTRA_HOURS_BEFORE_START = 3
    LIVE_HOURS_BEFORE_START = 2

    @classmethod
    def visibility_lead(cls) -> timedelta:
        return timedelta(
            days=cls.VISIBILITY_DAYS_BEFORE_START,
            hours=cls.VISIBILITY_EXTRA_HOURS_BEFORE_START,
        )

    @classmethod
    def live_lead(cls) -> timedelta:
        return timedelta(hours=cls.LIVE_HOURS_BEFORE_START)

    def visible_now(self):
        """Matches shown from 2d 3h before start until end time."""
        now = timezone.now()
        return self.filter(
            starts_at__lte=now + self.visibility_lead(),
            ends_at__gte=now,
        )


class Match(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    sport = models.CharField(max_length=64, db_index=True)
    home_team = models.CharField(max_length=128)
    away_team = models.CharField(max_length=128)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=MatchStatus.choices,
        default=MatchStatus.SCHEDULED,
        db_index=True,
    )
    poster_url = models.URLField(blank=True)
    match_number = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    tournament_group = models.CharField(max_length=8, blank=True)
    round = models.CharField(max_length=64, blank=True, db_index=True)
    venue = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=64, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MatchQuerySet.as_manager()

    class Meta:
        ordering = ["-sort_order", "starts_at"]
        indexes = [
            models.Index(fields=["status", "starts_at"]),
            models.Index(fields=["starts_at", "ends_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["sport", "match_number"],
                condition=models.Q(match_number__isnull=False),
                name="matches_unique_sport_match_number",
            ),
        ]

    def __str__(self) -> str:
        if self.title:
            return self.title
        return f"{self.home_team} vs {self.away_team}"

    @property
    def display_title(self) -> str:
        return self.title or f"{self.home_team} vs {self.away_team}"

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "End time must be after start time."})

    def is_visible_now(self) -> bool:
        now = timezone.now()
        lead = MatchQuerySet.visibility_lead()
        return self.starts_at - lead <= now <= self.ends_at


class Channel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="channels",
    )
    catalog_channel = models.ForeignKey(
        "catalog.CatalogChannel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_channels",
        help_text="Optional — pick from synced catalog or leave empty for a manual stream.",
    )
    name = models.CharField(max_length=128, blank=True)
    language = models.CharField(max_length=32, blank=True)
    logo_url = models.URLField(blank=True)
    stream_url = models.URLField(
        blank=True,
        help_text="HLS/m3u8 URL. Filled from catalog when selected, or enter your own.",
    )
    follow_catalog_stream = models.BooleanField(
        default=False,
        editable=False,
        help_text="When true, catalog sync updates this channel's stream URL automatically.",
    )
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    failure_count = models.PositiveIntegerField(default=0)
    deactivation_reason = models.CharField(
        max_length=32,
        choices=DeactivationReason.choices,
        blank=True,
        db_index=True,
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)
    url_updated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "match channel"
        verbose_name_plural = "match channels"
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["match", "priority"]),
        ]

    def __str__(self) -> str:
        return f"{self.match} — {self.name}"

    def apply_catalog_defaults(self) -> None:
        if not self.catalog_channel_id:
            return
        from catalog.grouping import primary_for_catalog

        catalog = primary_for_catalog(self.catalog_channel)
        self.catalog_channel = catalog

        custom_stream = bool(
            self.stream_url
            and self.pk
            and self.stream_url != catalog.stream_url
            and not self.follow_catalog_stream
        )

        self.name = catalog.name
        self.logo_url = catalog.logo_url
        self.language = catalog.region
        if not custom_stream:
            self.stream_url = catalog.stream_url

    def clean(self):
        super().clean()
        self.apply_catalog_defaults()
        if not self.stream_url:
            raise ValidationError(
                {"stream_url": "Enter a stream URL or choose a catalog channel."}
            )
        if not self.name:
            raise ValidationError(
                {"name": "Enter a channel name or choose a catalog channel."}
            )

    def save(self, *args, **kwargs):
        self.apply_catalog_defaults()
        if self.catalog_channel_id:
            self.follow_catalog_stream = (
                self.stream_url == self.catalog_channel.stream_url
            )
        else:
            self.follow_catalog_stream = False

        if self.pk:
            previous = Channel.objects.filter(pk=self.pk).only("stream_url").first()
            if previous and previous.stream_url != self.stream_url:
                self.url_updated_at = timezone.now()
                self.failure_count = 0
        super().save(*args, **kwargs)

    def failure_threshold(self, source: str = "system") -> int:
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
        from matches.cache import invalidate_match_caches

        invalidate_match_caches(match_id=self.match_id)
        if notify and reason in (DeactivationReason.USER_REPORTS, DeactivationReason.HEALTH_CHECK):
            from matches.notifications import notify_channel_deactivated

            notify_channel_deactivated(self, source=source or reason)

    def record_failure(self, source: str = "system") -> bool:
        """Increment failures; deactivate when threshold reached. Returns True if deactivated."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold(source):
            self.save(update_fields=["failure_count", "updated_at"])
            reason = (
                DeactivationReason.HEALTH_CHECK
                if source == "health_check"
                else DeactivationReason.USER_REPORTS
            )
            self.deactivate(reason, notify=True, source=source)
            return True
        self.save(update_fields=["failure_count", "updated_at"])
        return False

    def admin_reactivate(self) -> None:
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
        from matches.cache import invalidate_match_caches

        invalidate_match_caches(match_id=self.match_id)

    def reset_health(self) -> None:
        self.admin_reactivate()
