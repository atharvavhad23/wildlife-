"""
Bird URL routing: predictions, dashboards, and features.
"""

from django.urls import path
from predictor.views.bird_views import (
    birds_prediction,
    birds_photos_page,
    predict_birds_api,
    birds_result,
    birds_dashboard,
    get_birds_features,
    get_birds_photos,
    get_birds_clustering,
    get_birds_species_detail,
    get_birds_species_photos,
)

urlpatterns = [
    path('birds/', birds_prediction, name='birds'),
    path('birds/photos/', birds_photos_page, name='birds_photos_page'),
    path('predict/birds/', predict_birds_api, name='predict_birds'),
    path('predict/birds/result/', birds_result, name='birds_result'),
    path('dashboard/birds/', birds_dashboard, name='birds_dashboard'),
    path('features/birds/', get_birds_features, name='birds_features'),
    path('photos/birds/', get_birds_photos, name='birds_photos'),
    path('api/birds/clustering/', get_birds_clustering, name='birds_clustering_api'),
    path('api/birds/species/', get_birds_species_detail, name='birds_species_detail_api'),
    path('api/birds/species-photos/', get_birds_species_photos, name='birds_species_photos_api'),
]
