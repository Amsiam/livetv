from django.db import migrations, models

import catalog.field_limits as limits


class Migration(migrations.Migration):

    dependencies = [
        ("matches", "0008_match_schedule_metadata"),
        ("catalog", "0009_widen_catalogchannel_text_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="channel",
            name="name",
            field=models.CharField(
                blank=True,
                max_length=limits.CATALOG_NAME_MAX_LENGTH,
            ),
        ),
        migrations.AlterField(
            model_name="channel",
            name="logo_url",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="channel",
            name="stream_url",
            field=models.TextField(
                blank=True,
                help_text="HLS/m3u8 URL. Filled from catalog when selected, or enter your own.",
            ),
        ),
    ]
