from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0002_match_ends_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="channel",
            name="failure_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
