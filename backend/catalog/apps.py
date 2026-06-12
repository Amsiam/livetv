from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = "TV catalog"

    def ready(self):
        import catalog.signals  # noqa: F401, PLC0415
