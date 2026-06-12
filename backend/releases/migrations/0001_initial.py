from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AppRelease",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        choices=[("android", "Android")],
                        default="android",
                        max_length=20,
                    ),
                ),
                (
                    "version_name",
                    models.CharField(
                        help_text="Human-readable version, e.g. 1.0.1",
                        max_length=32,
                    ),
                ),
                (
                    "build_number",
                    models.PositiveIntegerField(
                        help_text="Must match Flutter pubspec build number (1.0.0+N).",
                    ),
                ),
                (
                    "min_build_number",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Users below this build are forced to update.",
                    ),
                ),
                (
                    "download_url",
                    models.URLField(
                        help_text="Direct HTTPS link to the APK file.",
                        max_length=2048,
                    ),
                ),
                (
                    "force_update",
                    models.BooleanField(
                        default=False,
                        help_text="When enabled, any user below build_number must update.",
                    ),
                ),
                ("release_notes", models.TextField(blank=True)),
                (
                    "is_published",
                    models.BooleanField(
                        default=True,
                        help_text="Only the latest published row per platform is served to the app.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-build_number", "-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="apprelease",
            constraint=models.UniqueConstraint(
                fields=("platform", "build_number"),
                name="releases_unique_platform_build",
            ),
        ),
    ]
