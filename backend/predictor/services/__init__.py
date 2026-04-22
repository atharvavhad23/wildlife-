"""
Services module initialization.
Exports model loading, prediction, preprocessing, and postprocessing services.
"""

from predictor.services.model_loader import ModelLoader
from predictor.services.prediction_service import (
    predict_animals,
    predict_birds,
    predict_insects,
    predict_plants,
    predict_occurrence_trend,
    build_birds_engineered_features,
    build_insects_engineered_features,
    build_plants_engineered_features,
    get_birds_thresholds,
    get_insects_thresholds,
    get_plants_thresholds,
    get_animals_thresholds,
)
from predictor.services.preprocessing import (
    safe_float,
    safe_number,
    safe_text,
    safe_round,
    normalize_species_text,
    extract_numeric_fields,
    validate_coordinate_range,
    validate_temporal_values,
    build_input_summary,
)
from predictor.services.postprocessing import (
    model_display_name,
    risk_level_from_prediction,
    status_from_risk,
    recommendation_from_risk,
    extract_feature_importance,
    build_gallery_row_from_dict,
    build_dashboard_stat,
    format_trend_data,
    format_environmental_data,
    paginate_results,
)

__all__ = [
    # Model Loader
    'ModelLoader',
    
    # Prediction Functions
    'predict_animals',
    'predict_birds',
    'predict_insects',
    'predict_plants',
    'predict_occurrence_trend',
    'build_birds_engineered_features',
    'build_insects_engineered_features',
    'build_plants_engineered_features',
    'get_birds_thresholds',
    'get_insects_thresholds',
    'get_plants_thresholds',
    'get_animals_thresholds',
    
    # Preprocessing
    'safe_float',
    'safe_number',
    'safe_text',
    'safe_round',
    'normalize_species_text',
    'extract_numeric_fields',
    'validate_coordinate_range',
    'validate_temporal_values',
    'build_input_summary',
    
    # Postprocessing
    'model_display_name',
    'risk_level_from_prediction',
    'status_from_risk',
    'recommendation_from_risk',
    'extract_feature_importance',
    'build_gallery_row_from_dict',
    'build_dashboard_stat',
    'format_trend_data',
    'format_environmental_data',
    'paginate_results',
]