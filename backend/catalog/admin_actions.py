from django.contrib import admin, messages

from catalog.deactivation import DeactivationReason
from health.stream_probe import probe_stream_url


class DeadLinkAdminActionsMixin:
    """List actions to deactivate channels with a dead stream URL."""

    @admin.action(description="Mark as dead link (deactivate)")
    def mark_dead_link(self, request, queryset):
        deactivated = 0
        for channel in queryset.filter(is_active=True):
            channel.deactivate(DeactivationReason.DEAD_LINK, notify=False)
            deactivated += 1
        if deactivated:
            self.message_user(
                request,
                f"Deactivated {deactivated} channel(s) as dead links. "
                "Review them under the inactive channels section.",
                messages.SUCCESS,
            )
        else:
            self.message_user(request, "No active channels were selected.", messages.WARNING)

    @admin.action(description="Probe stream URL — deactivate if unreachable")
    def probe_and_deactivate_if_dead(self, request, queryset):
        deactivated = 0
        skipped = 0
        for channel in queryset.filter(is_active=True):
            if probe_stream_url(channel.stream_url):
                skipped += 1
                continue
            channel.deactivate(DeactivationReason.DEAD_LINK, notify=False)
            deactivated += 1
        if deactivated:
            self.message_user(
                request,
                f"Deactivated {deactivated} dead link(s). {skipped} still responded.",
                messages.SUCCESS,
            )
        elif skipped:
            self.message_user(
                request,
                f"All {skipped} selected stream URL(s) responded — nothing deactivated.",
                messages.INFO,
            )
        else:
            self.message_user(request, "No active channels were selected.", messages.WARNING)
