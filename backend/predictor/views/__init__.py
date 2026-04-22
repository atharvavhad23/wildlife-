"""
Modular views package - organized by category.
All view functions are organized into category-specific modules for better maintainability.
"""

from .system_views import (
    send_email_otp,
    verify_email_otp,
    index,
    photo_proxy,
)

from .animal_views import (
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

from .bird_views import (
    birds_prediction,
    predict_birds_api,
    birds_result,
    birds_dashboard,
    get_birds_features,
    get_birds_photos,
    get_birds_clustering,
    get_birds_species_detail,
    get_birds_species_photos,
)

from .insect_views import (
    insects_prediction,
    predict_insects_api,
    insects_result,
    insects_dashboard,
    get_insects_features,
    get_insects_photos,
    get_insects_clustering,
    get_insects_species_detail,
    get_insects_species_photos,
)

from .plant_views import (
    predict_plants_api,
    get_plants_features,
    get_plants_clustering_api,
    get_plants_model_info,
    get_plants_photos,
)

from .analytics_views import (
    perform_clustering_api,
    get_species_detail_api,
    get_species_photos_api,
    get_gallery_photos_by_category,
    get_cluster_heatmap,
    get_cluster_details,
    get_cluster_timeline,
    get_seasonal_activity,
    get_conservation_alerts,
    get_top_observers,
    wildlife_dashboard,
)

__all__ = [
    # System
    'send_email_otp',
    'verify_email_otp',
    'index',
    'photo_proxy',
    
    # Animals
    'animals_prediction',
    'animals_photos_page',
    'predict_animals_api',
    'animals_result',
    'animals_dashboard',
    'get_animals_features',
    'get_animals_photos',
    'get_animals_clustering',
    'get_animals_species_detail',
    'get_animals_species_photos',
    
    # Birds
    'birds_prediction',
    'birds_photos_page',
    'predict_birds_api',
    'birds_result',
    'birds_dashboard',
    'get_birds_features',
    'get_birds_photos',
    'get_birds_clustering',
    'get_birds_species_detail',
    'get_birds_species_photos',
    
    # Insects
    'insects_prediction',
    'insects_photos_page',
    'predict_insects_api',
    'insects_result',
    'insects_dashboard',
    'get_insects_features',
    'get_insects_photos',
    'get_insects_clustering',
    'get_insects_species_detail',
    'get_insects_species_photos',
    
    # Plants
    'predict_plants_api',
    'get_plants_features',
    'get_plants_clustering_api',
    'get_plants_model_info',
    'get_plants_photos',
    
    # Analytics
    'perform_clustering_api',
    'get_species_detail_api',
    'get_species_photos_api',
    'get_gallery_photos_by_category',
    'get_cluster_heatmap',
    'get_cluster_details',
    'get_cluster_timeline',
    'get_seasonal_activity',
    'get_conservation_alerts',
    'get_top_observers',
    'wildlife_dashboard',
]
