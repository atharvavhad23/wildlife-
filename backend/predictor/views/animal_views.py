"""
Animal prediction views and dashboards.
"""

import json
import pandas as pd
import warnings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

import wildlife_config
from predictor.services import (
    predict_animals,
    extract_feature_importance,
    model_display_name,
    risk_level_from_prediction,
    status_from_risk,
    recommendation_from_risk,
    build_input_summary,
    safe_text,
    safe_round,
    safe_number,
    paginate_results,
)
from predictor.services.model_loader import ModelLoader
from predictor.constants import BASE_ANIMALS_FEATURES

warnings.filterwarnings('ignore')


@require_http_methods(["GET"])
def animals_prediction(request):
    """Render animals prediction page"""
    return render(request, 'animals.html', {'features': BASE_ANIMALS_FEATURES})


@csrf_exempt
@require_http_methods(["POST"])
def predict_animals_api(request):
    """API: Make an animal density prediction."""
    try:
        data = json.loads(request.body)
        result = predict_animals(data)

        model = ModelLoader.load_model('animals')

        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'model_name': model_display_name(model, 'RandomForestRegressor') if model else 'Animals Model',
            'status': 'success'
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)


@require_http_methods(["GET", "POST"])
def animals_result(request):
    """Render result page with prediction + environmental intelligence."""
    if request.method == "GET":
        return render(
            request,
            'result.html',
            {
                'prediction': None,
                'environmental_data': {},
                'decision': {},
                'species_label': 'Animals',
                'info': 'Submit an animal prediction to view a full conservation report.',
            },
        )

    try:
        payload = {k: v for k, v in request.POST.items()}
        result = predict_animals(payload)

        return render(
            request,
            'result.html',
            {
                'prediction': safe_round(result['prediction'], 4),
                'environmental_data': result['environmental_data'],
                'decision': result['decision'],
                'species_label': 'Animals',
            },
        )
    except Exception as e:
        return render(
            request,
            'result.html',
            {
                'error': str(e),
                'prediction': None,
                'environmental_data': {},
                'decision': {},
                'species_label': 'Animals',
            },
        )


@require_http_methods(["GET", "POST"])
def animals_dashboard(request):
    """Render dashboard for animal prediction output."""
    if request.method == "GET":
        return render(
            request,
            'dashboard.html',
            {
                'prediction': None,
                'species_label': 'Animals',
            },
        )

    try:
        payload = {k: v for k, v in request.POST.items()}
        result = predict_animals(payload)

        model = ModelLoader.load_model('animals')
        features = ModelLoader.load_feature_names('animals')
        input_data = result['model_input']
        env_data = result['environmental_data']
        prediction = result['prediction']

        context = {
            'species_label': 'Animals',
            'prediction': safe_round(prediction, 4),
            'environmental_data': env_data,
            'decision': result['decision'],
            'trend': result['trend'],
            'input_summary': build_input_summary(input_data),
            'chart_data': {
                'labels': [
                    'Temperature',
                    'Rainfall',
                    'Humidity',
                    'Vegetation',
                    'Water Availability',
                    'Human Disturbance',
                ],
                'values': [
                    safe_round(env_data.get('temperature', 0.0), 2),
                    safe_round(env_data.get('rainfall', 0.0), 2),
                    safe_round(env_data.get('humidity', 0.0), 2),
                    safe_round(env_data.get('vegetation_index', 0.0), 3),
                    safe_round(env_data.get('water_availability', 0.0), 3),
                    safe_round(env_data.get('human_disturbance', 0.0), 3),
                ],
            },
            'map_data': {
                'lat': safe_number(input_data.get('lat_grid', 0.0), 0.0),
                'lon': safe_number(input_data.get('lon_grid', 0.0), 0.0),
                'prediction': safe_round(prediction, 3),
                'prediction_normalized': min(100.0, max(0.0, prediction * 4.0)),
                'risk_level': result['decision'].get('risk_level', 'Medium'),
            },
            'feature_importance': extract_feature_importance(model, features, top_n=5),
        }

        return render(request, 'dashboard.html', context)
    except Exception as e:
        return render(
            request,
            'dashboard.html',
            {
                'error': str(e),
                'prediction': None,
                'species_label': 'Animals',
            },
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_animals_features(request):
    """Get base features for animals prediction"""
    return JsonResponse({
        'features': BASE_ANIMALS_FEATURES,
        'count': len(BASE_ANIMALS_FEATURES),
    })


@require_http_methods(["GET"])
def get_animals_photos(request):
    """Gallery endpoint: animal photos"""
    try:
        from predictor.views.analytics_views import get_gallery_photos_by_category
        return get_gallery_photos_by_category(request, 'animals')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_animals_clustering(request):
    """Perform K-means clustering for animals"""
    try:
        from predictor.views.analytics_views import perform_clustering_api
        return perform_clustering_api(request, 'animals')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_animals_species_detail(request):
    """Get detailed information about a specific animal species"""
    try:
        from predictor.views.analytics_views import get_species_detail_api
        return get_species_detail_api(request, 'animals')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_animals_species_photos(request):
    """Get photos for a specific animal species"""
    try:
        from predictor.views.analytics_views import get_species_photos_api
        return get_species_photos_api(request, 'animals')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
