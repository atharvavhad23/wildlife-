from django.apps import AppConfig

from apps.common.startup import bootstrap_backend


class SpeciesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.species'
    verbose_name = 'Species'

    def ready(self):
        bootstrap_backend()