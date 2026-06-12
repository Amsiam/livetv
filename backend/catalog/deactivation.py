from django.db import models


class DeactivationReason(models.TextChoices):
    USER_REPORTS = "user_reports", "User playback failures"
    SYNC_MISSING = "sync_missing", "Missing from catalog sync"
    HEALTH_CHECK = "health_check", "Server health check"
    DEAD_LINK = "dead_link", "Dead stream URL (admin)"
    UNSUPPORTED_FORMAT = "unsupported_format", "Unsupported stream format (non-HLS)"
    ADMIN = "admin", "Manual (admin)"
