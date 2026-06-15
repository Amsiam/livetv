from django.db import migrations, models

import catalog.field_limits as limits


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_catalogchannel_view_count"),
    ]

    operations = [
        migrations.AlterField(
            model_name="catalogchannel",
            name="category",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=limits.CATALOG_CATEGORY_MAX_LENGTH,
            ),
        ),
        migrations.AlterField(
            model_name="catalogchannel",
            name="name",
            field=models.CharField(
                db_index=True,
                max_length=limits.CATALOG_NAME_MAX_LENGTH,
            ),
        ),
        migrations.AlterField(
            model_name="catalogchannel",
            name="logo_url",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="catalogchannel",
            name="stream_url",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="catalogchannel",
            name="source_url",
            field=models.TextField(blank=True),
        ),
    ]
