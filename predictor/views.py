from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import joblib
import pandas as pd
import numpy as np
import json
import warnings

warnings.filterwarnings('ignore')

# Load animals model
try:
    animals_model = joblib.load('wildlife_model.pkl')
    animals_scaler = joblib.load('scaler.pkl')
    animals_features = joblib.load('feature_names.pkl')
    print("✓ Animals model loaded successfully!")
except Exception as e:
    print(f"Error loading animals model: {e}")
    animals_model = None

# Load birds model
try:
    birds_model = joblib.load('birds_model.pkl')
    birds_scaler = joblib.load('birds_scaler.pkl')
    birds_features = joblib.load('birds_feature_names.pkl')
    try:
        birds_metadata = joblib.load('birds_metadata.pkl')
    except Exception:
        birds_metadata = {}
    print("✓ Birds model loaded successfully!")
except Exception as e:
    print(f"Error loading birds model: {e}")
    birds_model = None


_birds_thresholds_cache = None


def _get_birds_thresholds():
    """Thresholds used by engineered binary features; cached after first load."""
    global _birds_thresholds_cache
    if _birds_thresholds_cache is not None:
        return _birds_thresholds_cache

    try:
        df = pd.read_csv('koyna_birds_regression_density.csv')
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
    return [
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
        
        input_data = {}
        for feature in animals_features:
            if feature in data:
                input_data[feature] = float(data[feature])
            else:
                return JsonResponse({
                    'error': f'Missing feature: {feature}',
                    'status': 'error'
                }, status=400)
        
        df_input = pd.DataFrame([input_data])
        df_scaled = animals_scaler.transform(df_input)
        prediction = animals_model.predict(df_scaled)[0]
        
        return JsonResponse({
            'prediction': float(prediction),
            'status': 'success'
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def predict_birds(request):
    """Make birds prediction"""
    try:
        data = json.loads(request.body)

        # Read only the 13 base inputs from UI, then engineer extra features server-side.
        base_input = {}
        for feature in _birds_base_feature_names():
            if feature not in data:
                return JsonResponse({'error': f'Missing feature: {feature}', 'status': 'error'}, status=400)
            base_input[feature] = float(data[feature])

        df_base = pd.DataFrame([base_input])
        df_engineered = _build_birds_engineered_features(df_base)

        # Align to the exact feature order the model was trained on.
        missing = [f for f in birds_features if f not in df_engineered.columns]
        if missing:
            return JsonResponse(
                {
                    'error': f"Model expects engineered features not available: {missing[:5]}" + ("..." if len(missing) > 5 else ""),
                    'status': 'error',
                },
                status=400,
            )

        df_input = df_engineered[birds_features]
        df_scaled = birds_scaler.transform(df_input)
        pred = float(birds_model.predict(df_scaled)[0])

        # If the birds model was trained on log1p(target), invert back to original scale.
        if isinstance(birds_metadata, dict) and birds_metadata.get('target_transform') == 'log1p':
            pred = float(np.expm1(pred))
        
        return JsonResponse({
            'prediction': float(pred),
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
        df = pd.read_csv('koyna_animals_regression_density.csv')
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
        df = pd.read_csv('koyna_birds_regression_density.csv')
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
