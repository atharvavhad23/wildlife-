"""
Animal URL routing: predictions, dashboards, and features.
"""

from django.urls import path
from predictor.views.animal_views import (
    animals_prediction,
    predict_animals_api,
    animals_result,
    animals_dashboard,
    get_animals_features,
    get_animals_photos,
    get_animals_clustering,
    get_animals_species_detail,
    get_animals_species_photos,
)

urlpatterns = [
    path('animals/', animals_prediction, name='animals'),
    path('predict/animals/', predict_animals_api, name='predict_animals'),
    path('predict/animals/result/', animals_result, name='animals_result'),
    path('dashboard/animals/', animals_dashboard, name='animals_dashboard'),
    path('features/animals/', get_animals_features, name='animals_features'),
    path('photos/animals/', get_animals_photos, name='animals_photos'),
    path('api/animals/clustering/', get_animals_clustering, name='animals_clustering_api'),
    path('api/animals/species/', get_animals_species_detail, name='species_detail_api'),
    path('api/animals/species-photos/', get_animals_species_photos, name='species_photos_api'),
]
