from django.apps import AppConfig

from apps.common.startup import bootstrap_backend


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analytics'
    verbose_name = 'Analytics'

    def ready(self):
        bootstrap_backend()