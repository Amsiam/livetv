from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from matches.cache import invalidate_match_caches
from matches.models import Channel, Match


@receiver(post_save, sender=Match)
def match_saved(sender, instance, **kwargs):
    invalidate_match_caches(match_id=instance.id)


@receiver(post_delete, sender=Match)
def match_deleted(sender, instance, **kwargs):
    invalidate_match_caches(match_id=instance.id)


@receiver(post_save, sender=Channel)
def channel_saved(sender, instance, **kwargs):
    invalidate_match_caches(match_id=instance.match_id)


@receiver(post_delete, sender=Channel)
def channel_deleted(sender, instance, **kwargs):
    invalidate_match_caches(match_id=instance.match_id)
