from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "search"

    def ready(self):
        # Importing for the signal side effects that keep the index fresh.
        from . import signals  # noqa: F401
