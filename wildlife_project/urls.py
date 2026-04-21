from django.contrib import admin
from django.urls import path
from predictor import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),
    path('animals/', views.animals_prediction, name='animals'),
    path('animals/photos/', views.animals_photos_page, name='animals_photos_page'),
    path('animals/clustering/', views.animals_clustering_map, name='animals_clustering_map'),
    path('animals/species/', views.species_detail_page, name='species_detail_page'),
    path('birds/', views.birds_prediction, name='birds'),
    path('birds/photos/', views.birds_photos_page, name='birds_photos_page'),
    path('insects/', views.insects_prediction, name='insects'),
    path('insects/photos/', views.insects_photos_page, name='insects_photos_page'),
    path('predict/animals/', views.predict_animals, name='predict_animals'),
    path('predict/animals/result/', views.animals_result, name='animals_result'),
    path('dashboard/animals/', views.animals_dashboard, name='animals_dashboard'),
    path('predict/birds/', views.predict_birds, name='predict_birds'),
    path('predict/birds/result/', views.birds_result, name='birds_result'),
    path('dashboard/birds/', views.birds_dashboard, name='birds_dashboard'),
    path('predict/insects/', views.predict_insects, name='predict_insects'),
    path('predict/insects/result/', views.insects_result, name='insects_result'),
    path('dashboard/insects/', views.insects_dashboard, name='insects_dashboard'),
    path('features/animals/', views.get_animals_features, name='animals_features'),
    path('photos/animals/', views.get_animals_photos, name='animals_photos'),
    path('photo-proxy/', views.photo_proxy, name='photo_proxy'),
    path('features/birds/', views.get_birds_features, name='birds_features'),
    path('photos/birds/', views.get_birds_photos, name='birds_photos'),
    path('features/insects/', views.get_insects_features, name='insects_features'),
    path('photos/insects/', views.get_insects_photos, name='insects_photos'),
    # API endpoints for clustering
    path('api/animals/clustering/', views.get_animals_clustering, name='animals_clustering_api'),
    path('api/animals/cluster-details/', views.get_cluster_details, name='cluster_details_api'),
    path('api/animals/cluster-heatmap/', views.get_cluster_heatmap, name='cluster_heatmap_api'),
    path('api/animals/species/', views.get_species_detail, name='species_detail_api'),
    path('api/animals/species-photos/', views.get_species_photos, name='species_photos_api'),
    path('api/inat-photos/', views.get_inat_photos, name='inat_photos_api'),
]
