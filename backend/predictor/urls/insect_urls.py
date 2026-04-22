"""
Insect URL routing: predictions, dashboards, and features.
"""

from django.urls import path
from predictor.views.insect_views import (
    insects_prediction,
    insects_photos_page,
    predict_insects_api,
    insects_result,
    insects_dashboard,
    get_insects_features,
    get_insects_photos,
    get_insects_clustering,
    get_insects_species_detail,
    get_insects_species_photos,
)

urlpatterns = [
    path('insects/', insects_prediction, name='insects'),
    path('insects/photos/', insects_photos_page, name='insects_photos_page'),
    path('predict/insects/', predict_insects_api, name='predict_insects'),
    path('predict/insects/result/', insects_result, name='insects_result'),
    path('dashboard/insects/', insects_dashboard, name='insects_dashboard'),
    path('features/insects/', get_insects_features, name='insects_features'),
    path('photos/insects/', get_insects_photos, name='insects_photos'),
    path('api/insects/clustering/', get_insects_clustering, name='insects_clustering_api'),
    path('api/insects/species/', get_insects_species_detail, name='insects_species_detail_api'),
    path('api/insects/species-photos/', get_insects_species_photos, name='insects_species_photos_api'),
]
