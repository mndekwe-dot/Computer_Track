from django.apps import AppConfig


class CampusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campus"

    def ready(self):
        # Registers the cache-invalidation receivers for rules and equipment
        # types. Imported here because signal handlers must not run at module
        # import time, before the app registry is populated.
        from . import signals  # noqa: F401
