from django.apps import AppConfig


class JiestoreappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'JieStoreApp'

    def ready(self):
        from . import signals  # noqa: F401
