from django.db import migrations, models


def backfill_group_keys(apps, schema_editor):
    CatalogChannel = apps.get_model("catalog", "CatalogChannel")
    import hashlib

    def make_group_key(region: str, name: str, category: str) -> str:
        raw = (
            f"{region.strip().lower()}|{name.strip().lower()}|"
            f"{category.strip().lower()}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    for channel in CatalogChannel.objects.all().iterator():
        channel.group_key = make_group_key(
            channel.region, channel.name, channel.category
        )
        channel.save(update_fields=["group_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_dead_link_deactivation_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogchannel",
            name="group_key",
            field=models.CharField(db_index=True, default="", max_length=64),
        ),
        migrations.RunPython(backfill_group_keys, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="catalogchannel",
            index=models.Index(
                fields=["group_key", "is_active"],
                name="catalog_cat_group_k_0f0f0d_idx",
            ),
        ),
    ]
