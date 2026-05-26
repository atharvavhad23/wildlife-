from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.http import JsonResponse

# Lazy-load predictor views; if ML stack is broken, create dummy views
try:
    from observations.predictor import views
    PREDICTOR_AVAILABLE = True
except (ImportError, SystemError):
    PREDICTOR_AVAILABLE = False
    # Create dummy views that return error responses if predictor can't load
    from django.http import JsonResponse
    def _predictor_error(request):
        return JsonResponse({'error': 'Predictor module unavailable (ML dependencies)'}, status=503)
    class views:
        index = _predictor_error
        animals_prediction = _predictor_error
        animals_photos_page = _predictor_error
        animals_clustering_map = _predictor_error
        species_detail_page = _predictor_error
        birds_prediction = _predictor_error
        birds_photos_page = _predictor_error
        insects_prediction = _predictor_error
        insects_photos_page = _predictor_error
        predict_animals = _predictor_error
        animals_result = _predictor_error
        animals_dashboard = _predictor_error
        predict_birds = _predictor_error
        birds_result = _predictor_error
        birds_dashboard = _predictor_error
        predict_insects = _predictor_error
        insects_result = _predictor_error
        insects_dashboard = _predictor_error
        predict_plants = _predictor_error
        get_plants_features = _predictor_error
        get_plants_clustering_api = _predictor_error
        get_plants_model_info = _predictor_error
        get_animals_features = _predictor_error
        get_animals_photos = _predictor_error
        get_birds_photos = _predictor_error
        get_insects_photos = _predictor_error
        get_plants_photos = _predictor_error
        photo_proxy = _predictor_error
        get_birds_features = _predictor_error
        get_insects_features = _predictor_error
        get_animals_clustering = _predictor_error
        get_species_detail = _predictor_error
        get_species_photos = _predictor_error
        get_birds_species_photos = _predictor_error
        get_insects_species_photos = _predictor_error
        get_plants_species_photos = _predictor_error
        get_birds_clustering = _predictor_error
        get_insects_clustering = _predictor_error
        get_birds_species_detail = _predictor_error
        get_insects_species_detail = _predictor_error
        get_plants_species_detail = _predictor_error
        get_cluster_heatmap = _predictor_error
        get_cluster_details = _predictor_error
        get_inat_photos = _predictor_error
        get_cluster_photos = _predictor_error
        get_species_observations = _predictor_error
        get_cluster_timeline = _predictor_error
        get_seasonal_activity = _predictor_error
        get_conservation_alerts = _predictor_error
        get_top_observers = _predictor_error
        get_dashboard_stats = _predictor_error
        wildlife_dashboard = _predictor_error
        send_email_otp = _predictor_error
        verify_email_otp = _predictor_error

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/send-otp/', views.send_email_otp, name='send_email_otp'),
    path('auth/verify-otp/', views.verify_email_otp, name='verify_email_otp'),
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
    path('photos/plants/', views.get_plants_photos, name='plants_photos'),
    path('features/plants/', views.get_plants_features, name='plants_features'),
    # Plants prediction & model
    path('predict/plants/', views.predict_plants, name='predict_plants'),
    path('api/plants/clustering/', views.get_plants_clustering_api, name='plants_clustering_api'),
    path('api/plants/model-info/', views.get_plants_model_info, name='plants_model_info_api'),
    # API endpoints for clustering
    path('api/animals/clustering/', views.get_animals_clustering, name='animals_clustering_api'),
    path('api/birds/clustering/', views.get_birds_clustering, name='birds_clustering_api'),
    path('api/insects/clustering/', views.get_insects_clustering, name='insects_clustering_api'),

    path('api/animals/species/', views.get_species_detail, name='species_detail_api'),
    path('api/birds/species/', views.get_birds_species_detail, name='birds_species_detail_api'),
    path('api/insects/species/', views.get_insects_species_detail, name='insects_species_detail_api'),
    path('api/plants/species/', views.get_plants_species_detail, name='plants_species_detail_api'),

    path('api/animals/species-photos/', views.get_species_photos, name='species_photos_api'),
    path('api/birds/species-photos/', views.get_birds_species_photos, name='birds_species_photos_api'),
    path('api/insects/species-photos/', views.get_insects_species_photos, name='insects_species_photos_api'),
    path('api/plants/species-photos/', views.get_plants_species_photos, name='plants_species_photos_api'),
    # New generic APIs (support ?dataset=animals|birds|insects|plants)
    path('api/cluster-heatmap/',      views.get_cluster_heatmap,      name='cluster_heatmap_api'),
    path('api/cluster-details/',      views.get_cluster_details,      name='cluster_details_api'),
    path('api/cluster-photos/',       views.get_cluster_photos,       name='cluster_photos_api'),
    path('api/inat-photos/',          views.get_inat_photos,          name='inat_photos_api'),
    path('api/species-observations/', views.get_species_observations, name='species_obs_api'),
    path('api/cluster-timeline/',     views.get_cluster_timeline,     name='cluster_timeline_api'),
    path('api/seasonal-activity/',    views.get_seasonal_activity,    name='seasonal_api'),
    path('api/conservation-alerts/',  views.get_conservation_alerts,  name='alerts_api'),
    path('api/top-observers/',        views.get_top_observers,        name='observers_api'),
    path('api/dashboard-stats/',      views.get_dashboard_stats,      name='dashboard_stats_api'),
    # Wildlife Intelligence Dashboard
    path('wildlife/dashboard/',       views.wildlife_dashboard,       name='wildlife_dashboard'),

    # API fallback: unknown API routes should never return SPA HTML.
    re_path(r'^api/.*$', lambda request: JsonResponse({'success': False, 'error': 'Not found'}, status=404)),

    # Catch-all for SPA routes (MUST be last)
    re_path(r'^.*$', views.index, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
