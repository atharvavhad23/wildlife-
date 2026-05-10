from django.urls import path

from .views import predict_view, prediction_history_view


urlpatterns = [
    path('', predict_view, name='predict'),
    path('history/', prediction_history_view, name='prediction-history'),
]