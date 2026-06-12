from django.db.models.signals import post_save
from django.dispatch import receiver

from catalog.cache import invalidate_catalog_caches
from catalog.models import CatalogChannel
from catalog.sync import propagate_linked_match_channels


@receiver(post_save, sender=CatalogChannel)
def on_catalog_channel_saved(sender, instance, **kwargs):
    if not instance.pk:
        return
    propagate_linked_match_channels(CatalogChannel.objects.filter(pk=instance.pk))
    invalidate_catalog_caches(channel_id=instance.pk)
