"""
Plant prediction views and dashboards.
"""

import json
import warnings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from predictor.services import (
    predict_plants,
    extract_feature_importance,
    model_display_name,
    build_input_summary,
    safe_text,
    safe_round,
    safe_number,
)
from predictor.services.model_loader import ModelLoader
from predictor.constants import BASE_PLANTS_FEATURES

warnings.filterwarnings('ignore')


@csrf_exempt
@require_http_methods(["POST"])
def predict_plants_api(request):
    """API: Make a plants density prediction."""
    try:
        data = json.loads(request.body)
        result = predict_plants(data)

        model = ModelLoader.load_model('plants')

        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'model_name': model_display_name(model, 'RandomForestRegressor') if model else 'Plants Model',
            'status': 'success'
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def get_plants_features(request):
    """Get base features for plants prediction"""
    try:
        features = ModelLoader.load_feature_names('plants')
        if not features:
            features = BASE_PLANTS_FEATURES
        
        return JsonResponse({
            'features': features,
            'count': len(features),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_plants_clustering_api(request):
    """Perform K-means clustering for plants"""
    try:
        from predictor.views.analytics_views import perform_clustering_api
        return perform_clustering_api(request, 'plants')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def get_plants_model_info(request):
    """Get plants model metadata and information"""
    try:
        model = ModelLoader.load_model('plants')
        metadata = ModelLoader.load_metadata('plants')
        features = ModelLoader.load_feature_names('plants')

        info = {
            'model_type': model.__class__.__name__ if model else 'Unknown',
            'features_count': len(features) if features else 0,
            'is_loaded': model is not None,
            'metadata': metadata if metadata else {},
        }

        if model and hasattr(model, 'feature_importances_'):
            feature_importance = extract_feature_importance(model, features, top_n=10)
            info['feature_importance'] = feature_importance

        return JsonResponse(info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_plants_photos(request):
    """Gallery endpoint: plant photos"""
    try:
        from predictor.views.analytics_views import get_gallery_photos_by_category
        return get_gallery_photos_by_category(request, 'plants')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
