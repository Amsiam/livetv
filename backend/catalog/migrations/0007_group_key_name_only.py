import hashlib

from django.db import migrations


def make_group_key(name: str) -> str:
    raw = name.strip().casefold()
    return hashlib.sha256(raw.encode()).hexdigest()


def backfill_group_keys(apps, schema_editor):
    CatalogChannel = apps.get_model("catalog", "CatalogChannel")
    for channel in CatalogChannel.objects.all().iterator():
        new_key = make_group_key(channel.name)
        if channel.group_key != new_key:
            channel.group_key = new_key
            channel.save(update_fields=["group_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_catalogchannel_group_key"),
    ]

    operations = [
        migrations.RunPython(backfill_group_keys, migrations.RunPython.noop),
    ]
