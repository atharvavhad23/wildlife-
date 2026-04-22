"""
Insect prediction views and dashboards.
"""

import json
import warnings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from predictor.services import (
    predict_insects,
    extract_feature_importance,
    model_display_name,
    build_input_summary,
    safe_text,
    safe_round,
    safe_number,
)
from predictor.services.model_loader import ModelLoader
from predictor.constants import BASE_INSECTS_FEATURES

warnings.filterwarnings('ignore')


@require_http_methods(["GET"])
def insects_prediction(request):
    """Render insects prediction page"""
    return render(request, 'insects.html', {'features': BASE_INSECTS_FEATURES})


@require_http_methods(["GET"])
def insects_photos_page(request):
    """Render dedicated insects photo gallery page."""
    return render(
        request,
        'photos_gallery.html',
        {
            'species_label': 'Insects',
            'photos_api': '/photos/insects/',
            'back_path': '/insects/',
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def predict_insects_api(request):
    """API: Make an insect prediction"""
    try:
        data = json.loads(request.body)
        result = predict_insects(data)

        model = ModelLoader.load_model('insects')

        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'model_name': model_display_name(model, 'RandomForestRegressor') if model else 'Insects Model',
            'status': 'success'
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)


@require_http_methods(["GET", "POST"])
def insects_result(request):
    """Render insect report page with prediction + environmental intelligence."""
    if request.method == "GET":
        return render(
            request,
            'result.html',
            {
                'prediction': None,
                'environmental_data': {},
                'decision': {},
                'species_label': 'Insects',
                'info': 'Submit an insect prediction to view a full conservation report.',
            },
        )

    try:
        payload = {k: v for k, v in request.POST.items()}
        result = predict_insects(payload)

        return render(
            request,
            'result.html',
            {
                'prediction': safe_round(result['prediction'], 4),
                'environmental_data': result['environmental_data'],
                'decision': result['decision'],
                'species_label': 'Insects',
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
                'species_label': 'Insects',
            },
        )


@require_http_methods(["GET", "POST"])
def insects_dashboard(request):
    """Render dashboard for insect prediction output."""
    if request.method == "GET":
        return render(
            request,
            'dashboard.html',
            {
                'prediction': None,
                'species_label': 'Insects',
            },
        )

    try:
        payload = {k: v for k, v in request.POST.items()}
        result = predict_insects(payload)

        model = ModelLoader.load_model('insects')
        features = ModelLoader.load_feature_names('insects')
        input_data = result['model_input']
        env_data = result['environmental_data']
        prediction = result['prediction']

        context = {
            'species_label': 'Insects',
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
                'species_label': 'Insects',
            },
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_insects_features(request):
    """Get base features for insects prediction"""
    return JsonResponse({
        'features': BASE_INSECTS_FEATURES,
        'count': len(BASE_INSECTS_FEATURES),
    })


@require_http_methods(["GET"])
def get_insects_photos(request):
    """Gallery endpoint: insect photos"""
    try:
        from predictor.views.analytics_views import get_gallery_photos_by_category
        return get_gallery_photos_by_category(request, 'insects')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_insects_clustering(request):
    """Perform K-means clustering for insects"""
    try:
        from predictor.views.analytics_views import perform_clustering_api
        return perform_clustering_api(request, 'insects')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_insects_species_detail(request):
    """Get detailed information about a specific insect species"""
    try:
        from predictor.views.analytics_views import get_species_detail_api
        return get_species_detail_api(request, 'insects')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_insects_species_photos(request):
    """Get photos for a specific insect species"""
    try:
        from predictor.views.analytics_views import get_species_photos_api
        return get_species_photos_api(request, 'insects')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
