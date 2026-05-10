from pathlib import Path

from django.apps import AppConfig

from apps.common.startup import bootstrap_backend


class ObservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.observations'
    path = str(Path(__file__).resolve().parent)

    def ready(self):
        bootstrap_backend()
