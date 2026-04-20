from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import joblib
import pandas as pd
import numpy as np
import json
import warnings
from pathlib import Path
from predictor.utils.environmental_data import get_environmental_data
from predictor.utils.decision_engine import analyze_prediction
from predictor.utils.trend_analysis import analyze_trend

warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _project_file(name: str) -> str:
    return str(PROJECT_ROOT / name)


BASE_BIRDS_FEATURES = [
    'coordinateUncertaintyInMeters',
    'day',
    'month',
    'year',
    'decade',
    'order_enc',
    'family_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
    'season_enc',
    'lat_grid',
    'lon_grid',
    'species_richness',
]


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_animals_lat_lon(payload: dict) -> tuple[float, float]:
    lat = _safe_float(payload.get('lat_grid'))
    lon = _safe_float(payload.get('lon_grid'))

    if lat is None:
        lat = _safe_float(payload.get('decimalLatitude'))
    if lon is None:
        lon = _safe_float(payload.get('decimalLongitude'))

    if lat is None or lon is None:
        raise ValueError('Latitude/longitude inputs are required (lat_grid/lon_grid).')
    return lat, lon


def _predict_animals_from_payload(payload: dict) -> dict:
    if animals_model is None or animals_scaler is None:
        raise ValueError('Animals model artifacts are not loaded.')

    lat, lon = _extract_animals_lat_lon(payload)
    env_data = get_environmental_data(lat, lon)

    model_input = {}
    for feature in animals_features:
        user_value = _safe_float(payload.get(feature))
        if user_value is not None:
            model_input[feature] = user_value
            continue

        if feature in env_data:
            model_input[feature] = float(env_data[feature])
            continue

        raise ValueError(f'Missing feature: {feature}')

    df_input = pd.DataFrame([model_input])
    df_scaled = animals_scaler.transform(df_input)
    prediction = float(animals_model.predict(df_scaled)[0])
    decision = analyze_prediction(prediction, env_data)
    trend = analyze_trend(prediction)

    return {
        'prediction': prediction,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': model_input,
    }


def _predict_birds_from_payload(payload: dict) -> dict:
    if birds_model is None or birds_scaler is None:
        raise ValueError('Bird prediction model is currently unavailable. Please retry shortly.')

    base_input = {}
    for feature in _birds_base_feature_names():
        value = _safe_float(payload.get(feature))
        if value is None:
            raise ValueError(f'Missing feature: {feature}')
        base_input[feature] = value

    df_base = pd.DataFrame([base_input])
    df_engineered = _build_birds_engineered_features(df_base)

    missing = [f for f in birds_features if f not in df_engineered.columns]
    if missing:
        msg = f"Model expects engineered features not available: {missing[:5]}"
        if len(missing) > 5:
            msg += "..."
        raise ValueError(msg)

    df_input = df_engineered[birds_features]
    df_scaled = birds_scaler.transform(df_input)
    pred = float(birds_model.predict(df_scaled)[0])

    if isinstance(birds_metadata, dict) and birds_metadata.get('target_transform') == 'log1p':
        pred = float(np.expm1(pred))

    env_data = get_environmental_data(base_input['lat_grid'], base_input['lon_grid'])
    decision = analyze_prediction(pred, env_data)
    trend = analyze_trend(pred)

    return {
        'prediction': pred,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': base_input,
    }


def _safe_round(value, decimals=3):
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return value


def _build_input_summary(input_data: dict, max_items: int = 12) -> list[dict]:
    summary = []
    for idx, (key, value) in enumerate(input_data.items()):
        if idx >= max_items:
            break
        summary.append(
            {
                'label': key.replace('_', ' ').title(),
                'value': _safe_round(value, 3),
            }
        )
    return summary


def _extract_feature_importance(model, feature_names, top_n=5):
    if model is None or not hasattr(model, 'feature_importances_'):
        return {'labels': [], 'values': []}

    try:
        importances = list(model.feature_importances_)
        pairs = list(zip(feature_names, importances))
        pairs.sort(key=lambda x: x[1], reverse=True)
        top_pairs = pairs[:top_n]
        return {
            'labels': [name for name, _ in top_pairs],
            'values': [round(float(score), 4) for _, score in top_pairs],
        }
    except Exception:
        return {'labels': [], 'values': []}


def _build_dashboard_context(species_label: str, result: dict, input_data: dict, model, feature_names):
    env = result['environmental_data']
    lat = float(input_data.get('lat_grid', 0.0))
    lon = float(input_data.get('lon_grid', 0.0))
    prediction = float(result['prediction'])

    prediction_normalized = min(100.0, max(0.0, prediction * 4.0))

    chart_data = {
        'labels': [
            'Temperature',
            'Rainfall',
            'Humidity',
            'Vegetation',
            'Water Availability',
            'Human Disturbance',
        ],
        'values': [
            _safe_round(env.get('temperature', 0.0), 2),
            _safe_round(env.get('rainfall', 0.0), 2),
            _safe_round(env.get('humidity', 0.0), 2),
            _safe_round(env.get('vegetation_index', 0.0), 3),
            _safe_round(env.get('water_availability', 0.0), 3),
            _safe_round(env.get('human_disturbance', 0.0), 3),
        ],
    }

    map_data = {
        'lat': lat,
        'lon': lon,
        'prediction': _safe_round(prediction, 3),
        'prediction_normalized': prediction_normalized,
        'risk_level': result['decision'].get('risk_level', 'Medium'),
    }

    feature_importance = _extract_feature_importance(model, feature_names, top_n=5)

    return {
        'species_label': species_label,
        'prediction': _safe_round(prediction, 4),
        'environmental_data': env,
        'decision': result['decision'],
        'trend': result['trend'],
        'input_summary': _build_input_summary(input_data),
        'chart_data': chart_data,
        'map_data': map_data,
        'feature_importance': feature_importance,
    }

# Load animals model
try:
    animals_model = joblib.load(_project_file('wildlife_model.pkl'))
    animals_scaler = joblib.load(_project_file('scaler.pkl'))
    animals_features = joblib.load(_project_file('feature_names.pkl'))
    print("Animals model loaded successfully.")
except Exception as e:
    print(f"Error loading animals model: {e}")
    animals_model = None

# Load birds artifacts
birds_model = None
birds_scaler = None
birds_features = BASE_BIRDS_FEATURES.copy()
birds_metadata = {}

try:
    try:
        birds_features = joblib.load(_project_file('birds_feature_names.pkl'))
    except Exception:
        birds_features = BASE_BIRDS_FEATURES.copy()

    birds_scaler = joblib.load(_project_file('birds_scaler.pkl'))
    birds_model = joblib.load(_project_file('birds_model.pkl'))
    try:
        birds_metadata = joblib.load(_project_file('birds_metadata.pkl'))
    except Exception:
        birds_metadata = {}
    print("Birds model loaded successfully.")
except Exception as e:
    print(f"Error loading birds model: {e}")


_birds_thresholds_cache = None


def _get_birds_thresholds():
    """Thresholds used by engineered binary features; cached after first load."""
    global _birds_thresholds_cache
    if _birds_thresholds_cache is not None:
        return _birds_thresholds_cache

    try:
        df = pd.read_csv(_project_file('koyna_birds_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'bird_sighting_density'])
        _birds_thresholds_cache = {
            'species_richness_median': float(X['species_richness'].median()),
            'coordinateUncertaintyInMeters_median': float(X['coordinateUncertaintyInMeters'].median()),
        }
    except Exception:
        _birds_thresholds_cache = {
            'species_richness_median': 0.0,
            'coordinateUncertaintyInMeters_median': 0.0,
        }

    return _birds_thresholds_cache


def _birds_base_feature_names():
    """The 13 raw features expected from the UI / dataset."""
    return BASE_BIRDS_FEATURES


def _build_birds_engineered_features(df_base: pd.DataFrame) -> pd.DataFrame:
    """Create the engineered features used by the latest birds model."""
    X = df_base.copy()
    thresholds = _get_birds_thresholds()

    # Interaction Terms
    X['order_family'] = X['order_enc'] * X['family_enc']
    X['richness_family'] = X['species_richness'] * X['family_enc']
    X['richness_order'] = X['species_richness'] * X['order_enc']
    X['order_family_rich'] = X['order_enc'] * X['family_enc'] * X['species_richness']

    # Spatial Interactions
    X['spatial'] = X['lat_grid'] * X['lon_grid']
    X['spatial_uncertainty'] = (X['lat_grid'] + X['lon_grid']) * X['coordinateUncertaintyInMeters']

    # Temporal Interactions
    X['season_month'] = X['season_enc'] * X['month']
    X['year_month'] = X['year'] * X['month']
    X['day_month'] = X['day'] * X['month']

    # Polynomial Features
    for feat in ['species_richness', 'month', 'day', 'year']:
        X[f'{feat}_sq'] = X[feat] ** 2
        X[f'{feat}_sqrt'] = np.sqrt(np.abs(X[feat]) + 1)
        X[f'{feat}_cbrt'] = np.cbrt(X[feat])

    # Log transforms
    X['richness_log'] = np.log1p(X['species_richness'])
    X['richness_log2'] = np.log1p(X['species_richness']) ** 2
    X['uncertainty_log'] = np.log1p(X['coordinateUncertaintyInMeters'])
    X['month_log'] = np.log1p(X['month'])

    # Ratios
    X['rich_uncertainty_ratio'] = X['species_richness'] / (X['coordinateUncertaintyInMeters'] + 1)
    X['family_order_ratio'] = (X['family_enc'] + 1) / (X['order_enc'] + 1)
    X['day_year_ratio'] = X['day'] / (X['year'] + 1)

    # Aggregates
    X['spatial_mean'] = (X['lat_grid'] + X['lon_grid']) / 2
    X['spatial_sum'] = X['lat_grid'] + X['lon_grid']
    X['temporal_mean'] = (X['day'] + X['month'] + X['decade']) / 3
    X['category_mean'] = (X['order_enc'] + X['family_enc'] + X['taxonRank_enc']) / 3

    # Binary features (use dataset medians, not single-row medians)
    X['richness_high'] = (X['species_richness'] > thresholds['species_richness_median']).astype(int)
    X['uncertainty_high'] = (
        X['coordinateUncertaintyInMeters'] > thresholds['coordinateUncertaintyInMeters_median']
    ).astype(int)
    X['month_season'] = (X['month'] % 4).astype(int)

    return X


def index(request):
    """Render the home page with both options"""
    return render(request, 'home.html')


def animals_prediction(request):
    """Render animals prediction page"""
    return render(request, 'animals.html', {'features': animals_features})


def birds_prediction(request):
    """Render birds prediction page"""
    return render(request, 'birds.html', {'features': birds_features})


@csrf_exempt
@require_http_methods(["POST"])
def predict_animals(request):
    """Make animal prediction"""
    try:
        data = json.loads(request.body)
        result = _predict_animals_from_payload(data)

        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
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
        result = _predict_animals_from_payload(payload)
        context = _build_dashboard_context('Animals', result, result['model_input'], animals_model, animals_features)
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

    try:
        payload = {k: v for k, v in request.POST.items()}
        result = _predict_animals_from_payload(payload)

        return render(
            request,
            'result.html',
            {
                'prediction': round(result['prediction'], 4),
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
def birds_result(request):
    """Render bird report page with prediction + environmental intelligence."""
    if request.method == "GET":
        return render(
            request,
            'result.html',
            {
                'prediction': None,
                'environmental_data': {},
                'decision': {},
                'species_label': 'Birds',
                'info': 'Submit a bird prediction to view a full conservation report.',
            },
        )

    try:
        payload = {k: v for k, v in request.POST.items()}
        result = _predict_birds_from_payload(payload)

        return render(
            request,
            'result.html',
            {
                'prediction': round(result['prediction'], 4),
                'environmental_data': result['environmental_data'],
                'decision': result['decision'],
                'species_label': 'Birds',
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
                'species_label': 'Birds',
            },
        )


@require_http_methods(["GET", "POST"])
def birds_dashboard(request):
    """Render dashboard for bird prediction output."""
    if request.method == "GET":
        return render(
            request,
            'dashboard.html',
            {
                'prediction': None,
                'species_label': 'Birds',
            },
        )

    try:
        payload = {k: v for k, v in request.POST.items()}
        result = _predict_birds_from_payload(payload)
        context = _build_dashboard_context('Birds', result, result['model_input'], birds_model, birds_features)
        return render(request, 'dashboard.html', context)
    except Exception as e:
        return render(
            request,
            'dashboard.html',
            {
                'error': str(e),
                'prediction': None,
                'species_label': 'Birds',
            },
        )


@csrf_exempt
@require_http_methods(["POST"])
def predict_birds(request):
    """Make birds prediction"""
    try:
        data = json.loads(request.body)
        result = _predict_birds_from_payload(data)
        
        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'status': 'success'
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)


@require_http_methods(["GET"])
def get_animals_features(request):
    """Return animal features and their ranges"""
    try:
        df = pd.read_csv(_project_file('koyna_animals_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'TARGET_sighting_density'])
        
        feature_info = {}
        for feature in animals_features:
            if feature in X.columns:
                feature_info[feature] = {
                    'min': float(X[feature].min()),
                    'max': float(X[feature].max()),
                    'mean': float(X[feature].mean()),
                    'std': float(X[feature].std())
                }
        
        return JsonResponse(feature_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_birds_features(request):
    """Return bird features and their ranges"""
    try:
        df = pd.read_csv(_project_file('koyna_birds_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'bird_sighting_density'])
        
        feature_info = {}
        # Expose only base/raw features to the UI.
        for feature in _birds_base_feature_names():
            if feature in X.columns:
                feature_info[feature] = {
                    'min': float(X[feature].min()),
                    'max': float(X[feature].max()),
                    'mean': float(X[feature].mean()),
                    'std': float(X[feature].std())
                }
        
        return JsonResponse(feature_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
