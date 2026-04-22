"""
Plant URL routing: predictions, dashboards, and features.
"""

from django.urls import path
from predictor.views.plant_views import (
    predict_plants_api,
    get_plants_features,
    get_plants_clustering_api,
    get_plants_model_info,
    get_plants_photos,
)

urlpatterns = [
    path('predict/plants/', predict_plants_api, name='predict_plants'),
    path('features/plants/', get_plants_features, name='plants_features'),
    path('photos/plants/', get_plants_photos, name='plants_photos'),
    path('api/plants/clustering/', get_plants_clustering_api, name='plants_clustering_api'),
    path('api/plants/model-info/', get_plants_model_info, name='plants_model_info_api'),
]
