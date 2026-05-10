from django.apps import AppConfig

from apps.common.startup import bootstrap_backend


class PredictionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.predictions'
    verbose_name = 'Predictions'

    def ready(self):
        bootstrap_backend()