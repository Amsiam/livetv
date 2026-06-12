from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def set_default_ends_at(apps, schema_editor):
    Match = apps.get_model("matches", "Match")
    for match in Match.objects.all():
        if match.ends_at is None:
            match.ends_at = match.starts_at + timedelta(hours=2)
            match.save(update_fields=["ends_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("matches", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="ends_at",
            field=models.DateTimeField(db_index=True, null=True),
        ),
        migrations.RunPython(set_default_ends_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="match",
            name="ends_at",
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AddIndex(
            model_name="match",
            index=models.Index(fields=["starts_at", "ends_at"], name="matches_mat_starts__a1b2c3_idx"),
        ),
    ]
