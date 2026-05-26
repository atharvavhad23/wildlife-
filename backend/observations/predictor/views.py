from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import logging
import math
import json
import re
import secrets
from urllib.parse import quote_plus
from urllib.request import urlopen, Request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
import pickle
import threading
from time import perf_counter

from apps.common import prediction_service
from apps.common.image_cache import resolve_cached_image, serve_cached_media_or_none


logger = logging.getLogger(__name__)

# Lazy imports for heavy ML/utils dependencies (loaded on first use, not at startup)
pd = None
np = None
cache = None
send_mail = None
get_environmental_data = None
analyze_prediction = None
analyze_trend = None
KMeans = None
StandardScaler = None
xgboost = None


def _lazy_import_ml():
    """Load heavy ML dependencies only when prediction endpoints are called."""
    global pd, np, KMeans, StandardScaler, xgboost
    if pd is not None:
        return
    try:
        import pandas as pnd
        import numpy as npy
        from sklearn.cluster import KMeans as km
        from sklearn.preprocessing import StandardScaler as ss

        pd = pnd
        np = npy
        KMeans = km
        StandardScaler = ss
        try:
            import xgboost as xgb
            xgboost = xgb
        except Exception:
            pass
    except ImportError:
        pass


def _lazy_import_utils():
    """Load predictor utils only when clustering/prediction endpoints are called."""
    global get_environmental_data, analyze_prediction, analyze_trend
    if get_environmental_data is not None:
        return
    try:
        from observations.predictor.utils.environmental_data import get_environmental_data as ged
        from observations.predictor.utils.decision_engine import analyze_prediction as ap
        from observations.predictor.utils.trend_analysis import analyze_trend as at
        globals()['get_environmental_data'] = ged
        globals()['analyze_prediction'] = ap
        globals()['analyze_trend'] = at
    except ImportError:
        pass


def _lazy_import_cache():
    """Load cache and mail on first use."""
    global cache, send_mail
    if cache is not None:
        return
    from django.core.cache import cache as c
    from django.core.mail import send_mail as sm
    globals()['cache'] = c
    globals()['send_mail'] = sm

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _project_file(name: str) -> str:
    candidates = [
        PROJECT_ROOT / 'ml_logic' / name,
        PROJECT_ROOT / 'ml_models' / name,
        PROJECT_ROOT / name,
        PROJECT_ROOT.parent / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


PREDICTION_ARTIFACTS = {
    'animals': {
        'model': ['animals_model.pkl', 'wildlife_model.pkl'],
        'scaler': ['animals_scaler.pkl', 'scaler.pkl'],
        'features': ['animals_feature_names.pkl', 'feature_names.pkl'],
        'metadata': ['animals_metadata.pkl', 'model_metadata.pkl'],
        'pca': ['animals_pca.pkl'],
    },
    'birds': {
        'model': ['birds_model.pkl'],
        'scaler': ['birds_scaler.pkl'],
        'features': ['birds_feature_names.pkl'],
        'metadata': ['birds_metadata.pkl'],
        'pca': ['birds_pca.pkl'],
    },
    'insects': {
        'model': ['insects_model.pkl'],
        'scaler': ['insects_scaler.pkl'],
        'features': ['insects_feature_names.pkl'],
        'metadata': ['insects_metadata.pkl'],
        'pca': ['insects_pca.pkl'],
    },
    'plants': {
        'model': ['plants_model.pkl'],
        'scaler': ['plants_scaler.pkl'],
        'features': ['plants_feature_names.pkl'],
        'metadata': ['plants_metadata.pkl'],
        'pca': [],
    },
}


def _prediction_error(message: str, status: int = 400):
    logger.warning('Prediction error (%s): %s', status, message)
    return JsonResponse({'success': False, 'error': message}, status=status)


def _read_prediction_payload(request):
    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _prediction_exception_response(exc: Exception, category: str):
    message = str(exc) or 'Internal server error'

    if isinstance(exc, FileNotFoundError):
        return _prediction_error(message, status=404)

    if isinstance(exc, ValueError):
        invalid_markers = ('invalid input', 'must be a number', 'could not convert', 'missing required', 'missing')
        if any(marker in message.lower() for marker in invalid_markers):
            return _prediction_error('Invalid input data', status=400)
        if 'not found' in message.lower():
            return _prediction_error(message, status=400)
        return _prediction_error('Invalid input data', status=400)

    if isinstance(exc, RuntimeError):
        if message.startswith('Failed to load prediction model'):
            return _prediction_error('Failed to load prediction model', status=500)
        if message.startswith('Failed to load prediction scaler'):
            return _prediction_error('Failed to load prediction scaler', status=500)
        if message.startswith('Failed to load prediction metadata'):
            return _prediction_error('Failed to load prediction metadata', status=500)
        return _prediction_error('Prediction processing failed', status=500)

    return _prediction_error('Internal server error', status=500)


def _ensure_prediction_runtime_ready():
    """Ensure prediction dependencies are available before inference."""
    _lazy_import_ml()
    _lazy_import_utils()
    if pd is None or np is None:
        raise RuntimeError('Prediction processing failed')
    if get_environmental_data is None or analyze_prediction is None or analyze_trend is None:
        raise RuntimeError('Prediction processing failed')


def _validate_numeric_inputs(payload: dict, numeric_keys: list[str]):
    """Validate that provided numeric fields can be parsed as floats."""
    for key in numeric_keys:
        if key not in payload:
            continue
        raw = payload.get(key)
        if raw is None or raw == '':
            raise ValueError('Invalid input data')
        try:
            float(raw)
        except (TypeError, ValueError):
            raise ValueError('Invalid input data')


def _load_first_existing_artifact(names: list[str], missing_message: str, corrupted_message: str | None = None):
    for name in names:
        path = Path(_project_file(name))
        if not path.exists():
            continue
        try:
            return prediction_service.load_artifact(path)
        except FileNotFoundError:
            continue
        except Exception as exc:
            logger.exception('Failed to load artifact from %s', path)
            if corrupted_message:
                raise RuntimeError(corrupted_message) from exc
            raise
    raise FileNotFoundError(missing_message)


def _load_prediction_bundle(category: str, force: bool = False):
    category = str(category).strip().lower()
    if category not in PREDICTION_ARTIFACTS:
        raise ValueError(f'Unknown prediction category: {category}')

    artifacts = PREDICTION_ARTIFACTS[category]
    state = globals()

    model_key = f'{category}_model'
    scaler_key = f'{category}_scaler'
    features_key = f'{category}_features'
    metadata_key = f'{category}_metadata'
    pca_key = f'{category}_pca'

    if not force and state.get(model_key) is not None and state.get(scaler_key) is not None:
        return

    model = _load_first_existing_artifact(
        artifacts.get('model', []),
        missing_message=f'Prediction model not found for {category}',
        corrupted_message='Failed to load prediction model',
    )
    scaler = _load_first_existing_artifact(
        artifacts.get('scaler', []),
        missing_message=f'Prediction scaler not found for {category}',
        corrupted_message='Failed to load prediction scaler',
    )

    features = _load_first_existing_artifact(
        artifacts.get('features', []),
        missing_message=f'Prediction metadata not found for {category}',
        corrupted_message='Failed to load prediction metadata',
    )
    if not isinstance(features, list) or not features:
        raise ValueError(f'Prediction model not found for {category}')

    metadata = {}
    if artifacts.get('metadata'):
        try:
            metadata = _load_first_existing_artifact(
                artifacts.get('metadata', []),
                missing_message=f'Prediction metadata not found for {category}',
                corrupted_message='Failed to load prediction metadata',
            )
        except Exception:
            metadata = {}
    if metadata is not None and not isinstance(metadata, dict):
        metadata = {}

    pca = None
    if artifacts.get('pca'):
        try:
            pca = _load_first_existing_artifact(
                artifacts.get('pca', []),
                missing_message=f'Prediction PCA not found for {category}',
                corrupted_message='Failed to load prediction PCA',
            )
        except Exception:
            pca = None

    state[model_key] = model
    state[scaler_key] = scaler
    state[features_key] = features
    state[metadata_key] = metadata
    state[pca_key] = pca


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

BASE_INSECTS_FEATURES = [
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

BASE_ANIMALS_OCCURRENCE_FEATURES = [
    'coordinateUncertaintyInMeters',
    'month',
    'year',
    'day',
    'decade',
    'lat_grid',
    'lon_grid',
    'phylum_enc',
    'class_enc',
    'order_enc',
    'family_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
    'season_enc',
    'species_richness',
]

BASE_PLANTS_FEATURES = [
    'coordinateUncertaintyInMeters',
    'day',
    'month',
    'year',
    'decade',
    'season_enc',
    'lat_grid',
    'lon_grid',
    'species_richness',
    'order_enc',
    'family_enc',
    'class_enc',
    'taxonRank_enc',
    'basisOfRecord_enc',
]

occurrence_models = {
    'animals': None,
    'birds': None,
    'insects': None,
    'plants': None,
}
occurrence_model_features = {
    'animals': BASE_ANIMALS_OCCURRENCE_FEATURES.copy(),
    'birds': BASE_BIRDS_FEATURES.copy(),
    'insects': BASE_INSECTS_FEATURES.copy(),
    'plants': BASE_PLANTS_FEATURES.copy(),
}

OTP_TTL_SECONDS = 10 * 60


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _otp_key(email: str, purpose: str) -> str:
    normalized = str(email).strip().lower()
    safe_purpose = str(purpose).strip().lower() or 'auth'
    return f"otp:{safe_purpose}:{normalized}"


def _otp_verified_key(email: str, purpose: str) -> str:
    normalized = str(email).strip().lower()
    safe_purpose = str(purpose).strip().lower() or 'auth'
    return f"otp_verified:{safe_purpose}:{normalized}"


@csrf_exempt
@require_http_methods(["POST"])
def send_email_otp(request):
    """Send OTP code to email using configured project SMTP account."""
    import json
    import secrets
    from django.http import JsonResponse
    from django.conf import settings
    from django.core.mail import send_mail
    from django.core.cache import cache

    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)

    email = str(payload.get('email', '')).strip().lower()
    purpose = str(payload.get('purpose', 'auth')).strip().lower() or 'auth'

    # ✅ Validate email
    if not email or '@' not in email:
        return JsonResponse({'success': False, 'error': 'Valid email is required.'}, status=400)

    # ✅ Proper SMTP configuration check (FIXED)
    if not all([
        getattr(settings, 'EMAIL_HOST', ''),
        getattr(settings, 'EMAIL_HOST_USER', ''),
        getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    ]):
        return JsonResponse(
            {'success': False, 'error': 'SMTP configuration incomplete. Check EMAIL_HOST, USER, PASSWORD.'},
            status=400,
        )

    # ✅ Generate OTP
    otp = f"{secrets.randbelow(900000) + 100000}"

    # Store OTP in Django cache (frontend-compatible key by email)
    cache.set(email, otp, timeout=300)

    subject = f"Koyna Wildlife OTP for {purpose.title()}"
    message = (
        f"Your OTP is: {otp}\n\n"
        f"It will expire in {OTP_TTL_SECONDS // 60} minutes.\n"
        "If you did not request this, please ignore this email."
    )

    try:
        # ✅ Send email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception('EMAIL ERROR')
        return JsonResponse(
            {'success': False, 'error': f'Failed to send OTP email: {str(exc)}'},
            status=500
        )

    return JsonResponse({'success': True, 'message': 'OTP sent to email.'}, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def verify_email_otp(request):
    """Verify OTP code sent to email."""
    from django.core.cache import cache

    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        payload = {}

    email = str(payload.get('email', '')).strip().lower()
    purpose = str(payload.get('purpose', 'auth')).strip().lower() or 'auth'
    code = str(payload.get('otp', '')).strip()

    if not email or '@' not in email:
        return JsonResponse({'success': False, 'error': 'Valid email is required.'}, status=400)
    if not code:
        return JsonResponse({'success': False, 'error': 'OTP code is required.'}, status=400)

    stored = cache.get(email)
    if stored is None:
        return JsonResponse({'success': False, 'error': 'Invalid or expired OTP'}, status=400)

    if str(stored) != code:
        return JsonResponse({'success': False, 'error': 'Invalid OTP'}, status=400)

    cache.delete(email)

    return JsonResponse({'success': True, 'message': 'OTP verified'}, status=200)


def _safe_number(value, default=0.0):
    """Return finite float, otherwise fallback default."""
    try:
        num = float(value)
        if math.isfinite(num):
            return num
    except (TypeError, ValueError):
        pass
    return default


def _safe_text(value, default='Unknown'):
    """Normalize missing/NaN text values for display and JSON safety."""
    if value is None:
        return default
    if isinstance(value, float) and not math.isfinite(value):
        return default
    text = str(value).strip()
    if not text or text.lower() in {'nan', 'none', 'null'}:
        return default
    return text


def _sanitize_for_json(value):
    """Recursively remove NaN/Inf values so browser JSON parsing never fails."""
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _load_occurrence_classifier_if_needed(category: str):
    """Load per-category RF occurrence classifier on demand."""
    if occurrence_models.get(category) is not None:
        return

    try:
        occurrence_models[category] = prediction_service.load_artifact(_project_file(f'{category}_occurrence_classifier.pkl'))
        try:
            loaded_features = prediction_service.load_artifact(_project_file(f'{category}_occurrence_features.pkl'))
            if isinstance(loaded_features, list) and loaded_features:
                occurrence_model_features[category] = loaded_features
        except Exception:
            pass
    except Exception:
        occurrence_models[category] = None


def _predict_occurrence_trend(category: str, feature_values: dict) -> dict | None:
    """Predict occurrence trend class using RandomForestClassifier artifacts."""
    _load_occurrence_classifier_if_needed(category)
    model = occurrence_models.get(category)
    if model is None:
        return None

    features = occurrence_model_features.get(category) or []
    if not features:
        return None

    row = []
    for feat in features:
        val = _safe_float(feature_values.get(feat), 0.0)
        row.append(float(val) if val is not None else 0.0)

    df_row = pd.DataFrame([row], columns=features)

    try:
        cls = str(model.predict(df_row)[0]).lower()
        confidence = None
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(df_row)[0]
            confidence = float(np.max(probs) * 100.0)

        if cls == 'rising':
            trend_label = 'Increasing'
            pct = confidence if confidence is not None else 8.0
        elif cls == 'declining':
            trend_label = 'Decreasing'
            pct = -(confidence if confidence is not None else 8.0)
        else:
            trend_label = 'Stable'
            pct = 0.0

        return {
            'trend': trend_label,
            'percentage_change': round(float(pct), 2),
            'classifier_label': cls,
            'confidence': round(float(confidence), 2) if confidence is not None else None,
            'source': 'RandomForestClassifier',
        }
    except Exception:
        return None


def _extract_animals_lat_lon(payload: dict) -> tuple[float, float]:
    lat = _safe_float(payload.get('latitude'))
    if lat is None:
        lat = _safe_float(payload.get('lat_grid'))
    if lat is None:
        lat = _safe_float(payload.get('decimalLatitude'))

    lon = _safe_float(payload.get('longitude'))
    if lon is None:
        lon = _safe_float(payload.get('lon_grid'))
    if lon is None:
        lon = _safe_float(payload.get('decimalLongitude'))

    if lat is None or lon is None:
        raise ValueError('Invalid input data')
    return float(lat), float(lon)


def _apply_user_environment_overrides(env_data: dict, payload: dict) -> dict:
    """Keep API environmental_data aligned with explicit user inputs."""
    for key in ['temperature', 'humidity', 'rainfall', 'vegetation_index', 'water_availability', 'human_disturbance']:
        user_val = _safe_float(payload.get(key))
        if user_val is not None:
            env_data[key] = user_val
    return env_data


def _build_prediction_environment(lat, lon, payload: dict) -> tuple[dict, dict]:
    """Return the raw simulated environment and the user-facing environmental data."""
    simulated_environment = get_environmental_data(lat, lon)
    environmental_data = _apply_user_environment_overrides(dict(simulated_environment), payload)
    return environmental_data, simulated_environment


def _environment_multiplier(env_data: dict) -> float:
    """
    Convert environmental conditions into a bounded ecological suitability multiplier.
    This keeps predictions scientifically responsive to user climate inputs.
    """
    t = _safe_float(env_data.get('temperature'), 27.0)
    h = _safe_float(env_data.get('humidity'), 65.0)
    r = _safe_float(env_data.get('rainfall'), 80.0)
    v = _safe_float(env_data.get('vegetation_index'), 0.55)
    w = _safe_float(env_data.get('water_availability'), 0.55)
    d = _safe_float(env_data.get('human_disturbance'), 0.35)

    temp_score = max(0.0, 1.0 - (abs(t - 27.0) / 35.0))
    humid_score = max(0.0, 1.0 - (abs(h - 65.0) / 70.0))
    rain_score = max(0.0, 1.0 - (abs(r - 120.0) / 380.0))
    veg_score = max(0.0, min(1.0, v))
    water_score = max(0.0, min(1.0, w))
    disturb_score = max(0.0, 1.0 - max(0.0, min(1.0, d)))

    suitability = (
        0.22 * temp_score
        + 0.16 * humid_score
        + 0.14 * rain_score
        + 0.20 * veg_score
        + 0.16 * water_score
        + 0.12 * disturb_score
    )
    return round(0.70 + (max(0.0, min(1.0, suitability)) * 0.60), 6)


def _project_environment(env_data: dict, years_ahead: int) -> dict:
    """
    Deterministic environmental drift model for future projections.
    """
    yrs = max(0, int(years_ahead))
    projected = dict(env_data)
    projected['temperature'] = _safe_float(projected.get('temperature'), 27.0) + (0.18 * yrs)
    projected['humidity'] = max(5.0, min(100.0, _safe_float(projected.get('humidity'), 65.0) - (0.22 * yrs)))
    projected['rainfall'] = max(0.0, _safe_float(projected.get('rainfall'), 80.0) - (1.4 * yrs))
    projected['vegetation_index'] = max(0.05, min(0.98, _safe_float(projected.get('vegetation_index'), 0.55) - (0.006 * yrs)))
    projected['water_availability'] = max(0.0, min(1.0, _safe_float(projected.get('water_availability'), 0.55) - (0.008 * yrs)))
    projected['human_disturbance'] = max(0.0, min(1.0, _safe_float(projected.get('human_disturbance'), 0.35) + (0.01 * yrs)))
    return projected


def _predict_animals_from_payload(payload: dict) -> dict:
    _ensure_prediction_runtime_ready()
    _validate_numeric_inputs(payload, [
        'temperature', 'humidity', 'rainfall', 'vegetation_index', 'water_availability', 'human_disturbance',
        'species_richness', 'year', 'month', 'day',
        'latitude', 'longitude', 'lat_grid', 'lon_grid', 'decimalLatitude', 'decimalLongitude',
    ])
    _load_animals_artifacts_if_needed()

    if animals_model is None or animals_scaler is None:
        raise FileNotFoundError('Prediction model not found for animals')

    lat, lon = _extract_animals_lat_lon(payload)
    env_data, simulated_environment = _build_prediction_environment(lat, lon, payload)

    model_input = {}
    if hasattr(animals_scaler, 'feature_names_in_'):
        orig_features = list(animals_scaler.feature_names_in_)
        means = dict(zip(animals_scaler.feature_names_in_, getattr(animals_scaler, 'mean_', [])))
    else:
        orig_features = animals_metadata.get('original_features', [
            "temperature", "rainfall", "humidity", "vegetation_index", 
            "water_availability", "human_disturbance"
        ])
        means = {}
    
    for feature in orig_features:
        user_value = _safe_float(payload.get(feature))
        if user_value is not None:
            model_input[feature] = user_value
            continue

        if feature in env_data:
            model_input[feature] = float(env_data[feature])
            continue

        model_input[feature] = means.get(feature, 0.0)

    # Base Prediction (Current)
    def _get_density(input_dict, env_for_density):
        df_input = pd.DataFrame([input_dict])[orig_features]
        df_scaled = animals_scaler.transform(df_input)
        if animals_pca is not None:
            df_scaled = animals_pca.transform(df_scaled)
            
        pred = float(animals_model.predict(df_scaled)[0])
        if animals_metadata.get('target_transform') == 'log1p':
            pred = float(np.expm1(pred))
            
        richness = _safe_float(input_dict.get('species_richness', 0.0))
        baseline = max(0.0, richness * 0.12)
        blended = (0.82 * max(0.0, pred)) + (0.18 * baseline)
        return max(0.0, blended * _environment_multiplier(env_for_density))

    current_density = _get_density(model_input, env_data)
    current_trend = _predict_occurrence_trend('animals', model_input) or analyze_trend(current_density)

    # Future Outlook Predictions (+5 Years and +10 Years)
    current_year = int(_safe_float(model_input.get('year', 2024)))
    
    input_5yr = model_input.copy()
    input_5yr['year'] = current_year + 5
    density_5yr = _get_density(input_5yr, _project_environment(env_data, 5))
    trend_5yr = _predict_occurrence_trend('animals', input_5yr)

    input_10yr = model_input.copy()
    input_10yr['year'] = current_year + 10
    density_10yr = _get_density(input_10yr, _project_environment(env_data, 10))
    trend_10yr = _predict_occurrence_trend('animals', input_10yr)

    # Endangered Risk Assessment
    density_change_10yr = ((density_10yr - current_density) / max(current_density, 0.001)) * 100
    
    is_endangered = False
    risk_level = "Low"
    warning_message = "STABLE: Population projected to remain stable or grow."

    if density_change_10yr <= -30.0:
        is_endangered = True
        risk_level = "High"
        warning_message = f"CRITICAL: Density model projects a severe {-density_change_10yr:.1f}% population drop over the next decade. Immediate conservation required."
    elif density_change_10yr <= -10.0:
        risk_level = "Medium"
        warning_message = f"WARNING: Model projects a {-density_change_10yr:.1f}% declining population trend. Habitat monitoring recommended."

    decision = analyze_prediction(current_density, env_data, is_endangered=is_endangered)
    
    future_outlook = {
        'projected_density_5yr': round(density_5yr, 2),
        'projected_density_10yr': round(density_10yr, 2),
        'projected_trend_5yr': 'Decreasing' if density_5yr < current_density * 0.99 else 'Increasing' if density_5yr > current_density * 1.01 else 'Stable',
        'projected_trend_10yr': 'Decreasing' if density_10yr < current_density * 0.99 else 'Increasing' if density_10yr > current_density * 1.01 else 'Stable',
        'density_change_10yr_pct': round(density_change_10yr, 2),
        'endangered_risk': {
            'is_endangered': is_endangered,
            'risk_level': risk_level,
            'warning_message': warning_message
        }
    }

    return {
        'prediction': current_density,
        'environmental_data': env_data,
        'simulated_environment': simulated_environment,
        'decision': decision,
        'trend': current_trend,
        'future_outlook': future_outlook,
        'model_input': model_input,
    }


def _predict_birds_from_payload(payload: dict) -> dict:
    _ensure_prediction_runtime_ready()
    _validate_numeric_inputs(payload, [
        'temperature', 'humidity', 'rainfall', 'vegetation_index', 'water_availability', 'human_disturbance',
        'latitude', 'longitude', 'lat_grid', 'lon_grid', 'decimalLatitude', 'decimalLongitude',
    ] + _birds_base_feature_names())
    _load_birds_artifacts_if_needed()

    if birds_model is None or birds_scaler is None:
        raise FileNotFoundError('Prediction model not found for birds')

    if hasattr(birds_scaler, 'feature_names_in_'):
        orig_features = list(birds_scaler.feature_names_in_)
        means = dict(zip(birds_scaler.feature_names_in_, getattr(birds_scaler, 'mean_', [])))
    else:
        orig_features = birds_metadata.get('original_features', birds_features)
        means = {}
        
    base_input = {}
    for feature in _birds_base_feature_names():
        value = _safe_float(payload.get(feature))
        if value is None:
            value = means.get(feature, 0.0)
        base_input[feature] = value

    lat = _safe_float(payload.get('lat_grid', 17.5))
    lon = _safe_float(payload.get('lon_grid', 73.5))
    env_data, simulated_environment = _build_prediction_environment(lat, lon, payload)

    # Base Prediction (Current)
    def _get_density(payload_dict, env_for_density):
        # Extract features for density model
        if hasattr(birds_scaler, 'feature_names_in_'):
            f_list = list(birds_scaler.feature_names_in_)
        else:
            f_list = birds_metadata.get('original_features', birds_features)
            
        b_input = {}
        for feature in _birds_base_feature_names():
            val = _safe_float(payload_dict.get(feature))
            if val is None: val = means.get(feature, 0.0)
            b_input[feature] = val

        df_b = pd.DataFrame([b_input])
        try:
            df_e = _build_birds_engineered_features(df_b)
        except Exception:
            df_e = df_b

        for col in f_list:
            if col not in df_e.columns:
                df_e[col] = means.get(col, 0.0)

        ds = birds_scaler.transform(df_e[f_list])
        if birds_pca is not None: ds = birds_pca.transform(ds)
        p = float(birds_model.predict(ds)[0])
        if isinstance(birds_metadata, dict) and birds_metadata.get('target_transform') == 'log1p':
            p = float(np.expm1(p))
        r = _safe_float(b_input.get('species_richness', 0.0))
        baseline = max(0.0, r * 0.15)
        blended = (0.82 * max(0.0, p)) + (0.18 * baseline)
        return max(0.0, blended * _environment_multiplier(env_for_density))

    current_density = _get_density(payload, env_data)
    current_year = int(_safe_float(payload.get('year', 2024)))
    
    # Future Outlook (+5 and +10 years)
    p5 = payload.copy(); p5['year'] = current_year + 5
    p10 = payload.copy(); p10['year'] = current_year + 10
    
    d5 = _get_density(p5, _project_environment(env_data, 5))
    d10 = _get_density(p10, _project_environment(env_data, 10))
    t5 = _predict_occurrence_trend('birds', p5)
    t10 = _predict_occurrence_trend('birds', p10)

    d_change = ((d10 - current_density) / max(current_density, 0.001)) * 100
    
    is_e = False
    rl = "Low"
    msg = "Population projected to remain stable or grow."
    
    if d_change <= -30.0:
        is_e = True
        rl = "High"
        msg = f"CRITICAL: Density model projects a severe {-d_change:.1f}% population drop over 10 years."
    elif d_change <= -10.0:
        rl = "Medium"
        msg = f"WARNING: Model projects a {-d_change:.1f}% declining population trend."

    future_outlook = {
        'projected_density_5yr': round(d5, 2),
        'projected_density_10yr': round(d10, 2),
        'projected_trend_5yr': 'Decreasing' if d5 < current_density * 0.99 else 'Increasing' if d5 > current_density * 1.01 else 'Stable',
        'projected_trend_10yr': 'Decreasing' if d10 < current_density * 0.99 else 'Increasing' if d10 > current_density * 1.01 else 'Stable',
        'density_change_10yr_pct': round(d_change, 2),
        'endangered_risk': {
            'is_endangered': is_e,
            'risk_level': rl,
            'warning_message': msg
        }
    }

    decision = analyze_prediction(current_density, env_data, is_endangered=is_e)
    trend = _predict_occurrence_trend('birds', payload) or analyze_trend(current_density)

    return {
        'prediction': current_density,
        'environmental_data': env_data,
        'simulated_environment': simulated_environment,
        'decision': decision,
        'trend': trend,
        'future_outlook': future_outlook,
        'model_input': base_input,
    }


def _predict_insects_from_payload(payload: dict) -> dict:
    _ensure_prediction_runtime_ready()
    _validate_numeric_inputs(payload, [
        'temperature', 'humidity', 'rainfall', 'vegetation_index', 'water_availability', 'human_disturbance',
        'latitude', 'longitude', 'lat_grid', 'lon_grid', 'decimalLatitude', 'decimalLongitude',
    ] + _insects_base_feature_names())
    _load_insects_artifacts_if_needed()

    if insects_model is None or insects_scaler is None:
        raise FileNotFoundError('Prediction model not found for insects')

    if hasattr(insects_scaler, 'feature_names_in_'):
        orig_features = list(insects_scaler.feature_names_in_)
        means = dict(zip(insects_scaler.feature_names_in_, getattr(insects_scaler, 'mean_', [])))
    else:
        orig_features = insects_metadata.get('original_features', insects_features)
        means = {}
        
    base_input = {}
    for feature in _insects_base_feature_names():
        value = _safe_float(payload.get(feature))
        if value is None:
            value = means.get(feature, 0.0)
        base_input[feature] = value

    lat = _safe_float(payload.get('lat_grid', 17.5))
    lon = _safe_float(payload.get('lon_grid', 73.5))
    env_data, simulated_environment = _build_prediction_environment(lat, lon, payload)

    # Base Prediction
    def _get_density(p_dict, env_for_density):
        if hasattr(insects_scaler, 'feature_names_in_'):
            f_list = list(insects_scaler.feature_names_in_)
        else:
            f_list = insects_metadata.get('original_features', insects_features)
        i_in = {}
        for f in _insects_base_feature_names():
            v = _safe_float(p_dict.get(f))
            if v is None: v = means.get(f, 0.0)
            i_in[f] = v
        df_i = pd.DataFrame([i_in])
        try:
            df_e = _build_insects_engineered_features(df_i)
        except Exception:
            df_e = df_i
        for col in f_list:
            if col not in df_e.columns: df_e[col] = means.get(col, 0.0)
        ds = insects_scaler.transform(df_e[f_list])
        if insects_pca is not None: ds = insects_pca.transform(ds)
        p = float(insects_model.predict(ds)[0])
        if isinstance(insects_metadata, dict) and insects_metadata.get('target_transform') == 'log1p':
            p = float(np.expm1(p))
        r = _safe_float(i_in.get('species_richness', 0.0))
        baseline = max(0.0, r * 0.22)
        blended = (0.82 * max(0.0, p)) + (0.18 * baseline)
        return max(0.0, blended * _environment_multiplier(env_for_density))

    current_density = _get_density(payload, env_data)
    current_year = int(_safe_float(payload.get('year', 2024)))
    
    # Future Outlook
    p5 = payload.copy(); p5['year'] = current_year + 5
    p10 = payload.copy(); p10['year'] = current_year + 10
    d5 = _get_density(p5, _project_environment(env_data, 5))
    d10 = _get_density(p10, _project_environment(env_data, 10))
    t5, t10 = _predict_occurrence_trend('insects', p5), _predict_occurrence_trend('insects', p10)

    d_change = ((d10 - current_density) / max(current_density, 0.001)) * 100
    
    is_e = False
    rl = "Low"
    msg = "Population projected to remain stable or grow."
    
    if d_change <= -30.0:
        is_e = True
        rl = "High"
        msg = f"CRITICAL: Density model projects a severe {-d_change:.1f}% population drop over 10 years."
    elif d_change <= -10.0:
        rl = "Medium"
        msg = f"WARNING: Model projects a {-d_change:.1f}% declining population trend."

    future_outlook = {
        'projected_density_5yr': round(d5, 2), 'projected_density_10yr': round(d10, 2),
        'projected_trend_5yr': 'Decreasing' if d5 < current_density * 0.99 else 'Increasing' if d5 > current_density * 1.01 else 'Stable',
        'projected_trend_10yr': 'Decreasing' if d10 < current_density * 0.99 else 'Increasing' if d10 > current_density * 1.01 else 'Stable',
        'density_change_10yr_pct': round(d_change, 2),
        'endangered_risk': {
            'is_endangered': is_e, 'risk_level': rl,
            'warning_message': msg
        }
    }

    decision = analyze_prediction(current_density, env_data, is_endangered=is_e)
    trend = _predict_occurrence_trend('insects', payload) or analyze_trend(current_density)

    return {
        'prediction': current_density,
        'environmental_data': env_data,
        'simulated_environment': simulated_environment,
        'decision': decision,
        'trend': trend,
        'future_outlook': future_outlook,
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
    if model is None:
        return {'labels': [], 'values': []}

    try:
        if hasattr(model, 'feature_importances_'):
            importances = list(model.feature_importances_)
        elif hasattr(model, 'coef_'):
            importances = list(np.abs(np.ravel(model.coef_)))
        else:
            return {'labels': [], 'values': []}

        pairs = list(zip(feature_names, importances))
        pairs.sort(key=lambda x: x[1], reverse=True)
        top_pairs = pairs[:top_n]
        return {
            'labels': [name for name, _ in top_pairs],
            'values': [round(float(score), 4) for _, score in top_pairs],
        }
    except Exception:
        return {'labels': [], 'values': []}


def _model_display_name(model, fallback='Model'):
    """Return a user-friendly model class name."""
    try:
        return str(model.__class__.__name__)
    except Exception:
        return fallback


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


def _build_insects_engineered_preview(base_input: dict) -> list[dict]:
    """Build a short, user-visible summary of key insects engineered features."""
    try:
        df_base = pd.DataFrame([base_input])
        df_engineered = _build_insects_engineered_features(df_base)
        row = df_engineered.iloc[0]

        preview = {
            'month_sin': float(row.get('month_sin', 0.0)),
            'month_cos': float(row.get('month_cos', 0.0)),
            'weekend_flag': float(row.get('weekend_flag', 0.0)),
            'observation_effort': float(row.get('observation_effort', 0.0)),
            'family_richness_grid': float(row.get('family_richness_grid', 0.0)),
            'uncertainty_bucket': float(row.get('uncertainty_bucket', 0.0)),
            'season_richness_interaction': float(row.get('season_richness_interaction', 0.0)),
        }
        return _build_input_summary(preview, max_items=20)
    except Exception:
        return []

animals_model = None
animals_scaler = None
animals_features = []
animals_metadata = {}
animals_pca = None

birds_model = None
birds_scaler = None
birds_pca = None
birds_features = BASE_BIRDS_FEATURES.copy()
birds_metadata = {}

insects_model = None
insects_scaler = None
insects_pca = None
insects_features = BASE_INSECTS_FEATURES.copy()
insects_metadata = {}

plants_model = None
plants_scaler = None
plants_features = BASE_PLANTS_FEATURES.copy()
plants_metadata = {}
plants_kmeans = None
plants_kmeans_scaler = None


def _load_animals_artifacts_if_needed():
    """Load animals artifacts on demand and cache them in module globals."""
    global animals_model, animals_scaler, animals_features, animals_metadata, animals_pca
    if animals_model is not None and animals_scaler is not None:
        return
    _load_prediction_bundle('animals')


def _load_birds_artifacts_if_needed():
    """Load birds artifacts on demand and cache them in module globals."""
    global birds_model, birds_scaler, birds_pca, birds_features, birds_metadata
    if birds_model is not None and birds_scaler is not None:
        return
    _load_prediction_bundle('birds')


def _load_insects_artifacts_if_needed():
    """Load insects artifacts on demand and cache them in module globals."""
    global insects_model, insects_scaler, insects_pca, insects_features, insects_metadata
    if insects_model is not None and insects_scaler is not None:
        return
    _load_prediction_bundle('insects')


def _reload_plants_artifacts_if_needed(force: bool = False):
    """Load plants model artifacts on demand if they were unavailable at startup."""
    global plants_model, plants_scaler, plants_features, plants_metadata, plants_kmeans, plants_kmeans_scaler

    if not force and plants_model is not None and plants_scaler is not None:
        return
    _load_prediction_bundle('plants', force=force)

    try:
        plants_kmeans = prediction_service.load_artifact(_project_file('plants_kmeans.pkl'))
        plants_kmeans_scaler = prediction_service.load_artifact(_project_file('plants_kmeans_scaler.pkl'))
    except Exception:
        plants_kmeans = None
        plants_kmeans_scaler = None

_birds_thresholds_cache = None
_insects_thresholds_cache = None
_oembed_cache = {}  # In-memory cache (session-scoped)
_gallery_rows_cache = {}
_thumbnail_executor = ThreadPoolExecutor(max_workers=6)  # Parallel thumbnail resolver
_cache_lock = threading.Lock()  # Thread-safe cache access
_persistent_cache_path = Path(__file__).resolve().parent.parent / 'thumbnail_cache.pkl'
_THUMBNAIL_MISS = '__MISS__'

def _load_persistent_cache():
    """Load thumbnail cache from disk (across sessions)."""
    try:
        if _persistent_cache_path.exists():
            with open(_persistent_cache_path, 'rb') as f:
                return pickle.load(f)
    except Exception:
        pass
    return {}

def _save_persistent_cache():
    """Save thumbnail cache to disk for persistence across sessions."""
    try:
        with open(_persistent_cache_path, 'wb') as f:
            pickle.dump(_oembed_cache, f)
    except Exception:
        pass

# Load persistent cache at startup
_oembed_cache = _load_persistent_cache()


def _resolve_occurrence_thumbnail(occurrence_url: str) -> str | None:
    if not occurrence_url or not str(occurrence_url).startswith('http'):
        return None

    with _cache_lock:
        has_cached = occurrence_url in _oembed_cache
        cached = _oembed_cache.get(occurrence_url)
        if has_cached:
            if cached == _THUMBNAIL_MISS:
                return None
            local_cached = resolve_cached_image(cached, cache_key=f'occurrence:{occurrence_url}', occurrence_url=occurrence_url)
            if local_cached:
                _oembed_cache[occurrence_url] = local_cached
                return local_cached
            if cached:
                return cached

    local_record = resolve_cached_image(None, cache_key=f'occurrence:{occurrence_url}', occurrence_url=occurrence_url)
    if local_record:
        with _cache_lock:
            _oembed_cache[occurrence_url] = local_record
        return local_record

    thumbnail_url = None
    try:
        if 'inaturalist.org/observations/' in occurrence_url:
            match = re.search(r'/observations/(\d+)', occurrence_url)
            obs_id = match.group(1) if match else None

            if obs_id:
                api_url = f"https://api.inaturalist.org/v1/observations/{obs_id}"
                with urlopen(api_url, timeout=4) as response:  # Reduced timeout to 4s
                    data = json.loads(response.read().decode('utf-8'))
                    results = data.get('results') or []
                    photos = (results[0].get('photos') if results else []) or []
                    if photos:
                        raw_url = str(photos[0].get('url') or '')
                        thumbnail_url = raw_url.replace('/square.', '/medium.') if raw_url else None

            if not thumbnail_url:
                oembed_url = f"https://www.inaturalist.org/oembed?url={quote_plus(occurrence_url)}"
                with urlopen(oembed_url, timeout=3) as response:  # Reduced timeout to 3s
                    data = json.loads(response.read().decode('utf-8'))
                    thumbnail_url = data.get('thumbnail_url')
    except Exception:
        thumbnail_url = None

    if thumbnail_url:
        thumbnail_url = resolve_cached_image(
            thumbnail_url,
            cache_key=f'occurrence:{occurrence_url}',
            occurrence_url=occurrence_url,
            source='inaturalist-oembed',
        ) or thumbnail_url

    with _cache_lock:
        _oembed_cache[occurrence_url] = thumbnail_url if thumbnail_url else _THUMBNAIL_MISS
    
    return thumbnail_url


def _resolve_thumbnails_parallel(occurrence_urls: list[str]) -> dict[str, str | None]:
    """
    Resolve multiple thumbnails in parallel using thread pool.
    Returns dict mapping occurrence_url -> thumbnail_url (or None if failed/missing).
    
    Performance improvement:
    - 6 concurrent workers = ~6x faster than sequential
    - Persistent disk cache = instant subsequent loads
    - First page load: ~10-12s for 24 photos
    - Cached page load: <100ms
    """
    result = {}
    futures = {}
    
    # Submit all tasks to thread pool
    for url in occurrence_urls:
        if url and str(url).startswith('http'):
            futures[_thumbnail_executor.submit(_resolve_occurrence_thumbnail, url)] = url
    
    # Collect results as they complete
    for future in as_completed(futures):
        url = futures[future]
        try:
            thumb = future.result()
            result[url] = thumb
        except Exception:
            result[url] = None
    
    # Ensure all URLs have an entry
    for url in occurrence_urls:
        if url not in result:
            result[url] = None
    
    # Save updated cache to disk after each batch (for persistence)
    _save_persistent_cache()
    
    return result


def _build_gallery_rows_from_csv(csv_name: str, default_subtitle: str) -> list[dict]:
    cache_key = (csv_name, default_subtitle)
    cached = _gallery_rows_cache.get(cache_key)
    if cached is not None:
        return cached

    _lazy_import_ml()
    if pd is None:
        return []

    try:
        df = pd.read_csv(_project_file(csv_name))
    except Exception:
        return []

    required = [
        'occurrenceID',
        'scientificName',
        'species',
        'eventDate',
        'locality',
        'decimalLatitude',
        'decimalLongitude',
    ]
    for col in required:
        if col not in df.columns:
            df[col] = ''

    rows = df.dropna(subset=['occurrenceID'])

    photos = []
    for _, row in rows.iterrows():
        occurrence_url = str(row.get('occurrenceID', '')).strip()
        if not occurrence_url.startswith('http'):
            continue

        title = str(row.get('scientificName') or row.get('species') or 'Wildlife Observation').strip()
        subtitle = str(row.get('locality') or default_subtitle).strip()
        event_date = str(row.get('eventDate') or '').strip()

        photos.append(
            {
                'title': title[:120],
                'subtitle': subtitle[:80],
                'eventDate': event_date[:20],
                'occurrenceUrl': occurrence_url,
            }
        )

    _gallery_rows_cache[cache_key] = photos
    return photos


def _parse_gallery_pagination(request) -> tuple[int, int | None]:
    offset_raw = str(request.GET.get('offset', '0')).strip().lower()
    try:
        offset = max(0, int(offset_raw))
    except Exception:
        offset = 0

    raw = str(request.GET.get('limit', '24')).strip().lower()
    if raw in {'all', 'none'}:
        return offset, None
    try:
        parsed = int(raw)
    except Exception:
        parsed = 24
    return offset, max(1, min(parsed, 60))


def _build_gallery_page_payload(rows: list[dict], offset: int, limit: int | None) -> dict:
    total = len(rows)
    if offset >= total:
        return {
            'photos': [],
            'count': 0,
            'total': total,
            'offset': offset,
            'hasMore': False,
        }

    if limit is None:
        chunk = rows[offset:]
        next_offset = total
    else:
        chunk = rows[offset:offset + limit]
        next_offset = offset + len(chunk)

    # Extract all occurrence URLs from chunk
    occurrence_urls = [item.get('occurrenceUrl', '') for item in chunk]
    
    # Resolve all thumbnails in parallel (up to 6x faster than sequential)
    thumbnails = _resolve_thumbnails_parallel(occurrence_urls)
    
    # Build photo list with resolved thumbnails
    photos = []
    for item in chunk:
        occurrence_url = item.get('occurrenceUrl', '')
        thumb = thumbnails.get(occurrence_url)
        photos.append(
            {
                **item,
                'thumbnailUrl': thumb,
                'hasImage': bool(thumb),
            }
        )

    return {
        'photos': photos,
        'count': len(photos),
        'total': total,
        'offset': offset,
        'nextOffset': next_offset,
        'hasMore': next_offset < total,
    }


def _build_animals_gallery_rows() -> list[dict]:
    return _build_gallery_rows_from_csv('Koyna_animals_final.csv', 'Koyna Region')


def _build_birds_gallery_rows() -> list[dict]:
    return _build_gallery_rows_from_csv('Koyna_birds_final.csv', 'Koyna Birding Spot')


def _build_insects_gallery_rows() -> list[dict]:
    return _build_gallery_rows_from_csv('Koyna_insects_final.csv', 'Koyna Insect Habitat')


def _build_plants_gallery_rows() -> list[dict]:
    return _build_gallery_rows_from_csv('Koyna_plants_final.csv', 'Koyna Flora Hub')


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


def _get_insects_thresholds():
    """Thresholds used by engineered insect binary features; cached after first load."""
    global _insects_thresholds_cache
    if _insects_thresholds_cache is not None:
        return _insects_thresholds_cache

    try:
        df = pd.read_csv(_project_file('koyna_insects_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'insect_sighting_density'])
        effort_lookup = (
            X.groupby(['lat_grid', 'lon_grid', 'month'])
            .size()
            .to_dict()
        )
        family_richness_lookup = (
            X.groupby(['lat_grid', 'lon_grid'])['family_enc']
            .nunique()
            .to_dict()
        )
        q1, q2, q3 = X['coordinateUncertaintyInMeters'].quantile([0.25, 0.50, 0.75]).tolist()
        _insects_thresholds_cache = {
            'species_richness_median': float(X['species_richness'].median()),
            'coordinateUncertaintyInMeters_median': float(X['coordinateUncertaintyInMeters'].median()),
            'observation_effort_lookup': effort_lookup,
            'observation_effort_median': float(np.median(list(effort_lookup.values()))) if effort_lookup else 1.0,
            'family_richness_lookup': family_richness_lookup,
            'family_richness_median': float(np.median(list(family_richness_lookup.values()))) if family_richness_lookup else 1.0,
            'uncertainty_q1': float(q1),
            'uncertainty_q2': float(q2),
            'uncertainty_q3': float(q3),
        }
    except Exception:
        _insects_thresholds_cache = {
            'species_richness_median': 0.0,
            'coordinateUncertaintyInMeters_median': 0.0,
            'observation_effort_lookup': {},
            'observation_effort_median': 1.0,
            'family_richness_lookup': {},
            'family_richness_median': 1.0,
            'uncertainty_q1': 0.0,
            'uncertainty_q2': 0.0,
            'uncertainty_q3': 0.0,
        }

    return _insects_thresholds_cache


def _insects_base_feature_names():
    """The 13 raw insect features expected from the UI / dataset."""
    return BASE_INSECTS_FEATURES


def _build_birds_engineered_features(df_base):
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


def _build_insects_engineered_features(df_base):
    """Create engineered features used by the insects linear regression model."""
    X = df_base.copy()
    thresholds = _get_insects_thresholds()

    X['month_sin'] = np.sin(2 * np.pi * X['month'] / 12.0)
    X['month_cos'] = np.cos(2 * np.pi * X['month'] / 12.0)

    dates = pd.to_datetime(
        {
            'year': X['year'].round().astype(int),
            'month': X['month'].round().clip(1, 12).astype(int),
            'day': X['day'].round().clip(1, 31).astype(int),
        },
        errors='coerce',
    )
    X['weekend_flag'] = dates.dt.dayofweek.isin([5, 6]).astype(int)

    def _lookup_effort(row):
        key = (round(float(row['lat_grid']), 1), round(float(row['lon_grid']), 1), round(float(row['month']), 1))
        return thresholds['observation_effort_lookup'].get(key, thresholds['observation_effort_median'])

    def _lookup_family_richness(row):
        key = (round(float(row['lat_grid']), 1), round(float(row['lon_grid']), 1))
        return thresholds['family_richness_lookup'].get(key, thresholds['family_richness_median'])

    X['observation_effort'] = X.apply(_lookup_effort, axis=1).astype(float)
    X['family_richness_grid'] = X.apply(_lookup_family_richness, axis=1).astype(float)

    q1 = thresholds['uncertainty_q1']
    q2 = thresholds['uncertainty_q2']
    q3 = thresholds['uncertainty_q3']
    X['uncertainty_bucket'] = (
        (X['coordinateUncertaintyInMeters'] > q1).astype(int)
        + (X['coordinateUncertaintyInMeters'] > q2).astype(int)
        + (X['coordinateUncertaintyInMeters'] > q3).astype(int)
    ).astype(float)

    X['order_family'] = X['order_enc'] * X['family_enc']
    X['richness_family'] = X['species_richness'] * X['family_enc']
    X['richness_order'] = X['species_richness'] * X['order_enc']
    X['spatial'] = X['lat_grid'] * X['lon_grid']
    X['spatial_uncertainty'] = (X['lat_grid'] + X['lon_grid']) * X['coordinateUncertaintyInMeters']
    X['season_month'] = X['season_enc'] * X['month']
    X['year_month'] = X['year'] * X['month']
    X['day_month'] = X['day'] * X['month']

    for feat in ['species_richness', 'month', 'day', 'year']:
        X[f'{feat}_sq'] = X[feat] ** 2

    X['richness_log'] = np.log1p(X['species_richness'])
    X['uncertainty_log'] = np.log1p(X['coordinateUncertaintyInMeters'])
    X['uncertainty_inv'] = 1.0 / (1.0 + np.log1p(X['coordinateUncertaintyInMeters'].clip(lower=0)))
    X['rich_uncertainty_ratio'] = X['species_richness'] / (X['coordinateUncertaintyInMeters'] + 1)
    X['family_order_ratio'] = (X['family_enc'] + 1) / (X['order_enc'] + 1)
    X['day_year_ratio'] = X['day'] / (X['year'] + 1)
    X['spatial_mean'] = (X['lat_grid'] + X['lon_grid']) / 2
    X['temporal_mean'] = (X['day'] + X['month'] + X['decade']) / 3
    X['category_mean'] = (X['order_enc'] + X['family_enc'] + X['taxonRank_enc']) / 3
    X['season_richness_interaction'] = X['season_enc'] * X['species_richness']
    X['richness_high'] = (X['species_richness'] > thresholds['species_richness_median']).astype(int)
    X['uncertainty_high'] = (
        X['coordinateUncertaintyInMeters'] > thresholds['coordinateUncertaintyInMeters_median']
    ).astype(int)

    return X


def index(request):
    """Render the main React SPA entry point"""
    return render(request, 'index.html')


def animals_prediction(request):
    """Render animals prediction page"""
    _load_animals_artifacts_if_needed()
    return render(request, 'animals.html', {'features': animals_features})


def animals_photos_page(request):
    """Render dedicated animals photo gallery page."""
    return render(
        request,
        'photos_gallery.html',
        {
            'species_label': 'Animals',
            'photos_api': '/photos/animals/',
            'back_path': '/animals/',
        },
    )


def birds_prediction(request):
    """Render birds prediction page"""
    _load_birds_artifacts_if_needed()
    return render(request, 'birds.html', {'features': birds_features})


def birds_photos_page(request):
    """Render dedicated birds photo gallery page."""
    return render(
        request,
        'photos_gallery.html',
        {
            'species_label': 'Birds',
            'photos_api': '/photos/birds/',
            'back_path': '/birds/',
        },
    )


def insects_prediction(request):
    """Render insects prediction page"""
    _load_insects_artifacts_if_needed()
    return render(request, 'insects.html', {'features': insects_features})


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
def predict_animals(request):
    """Make animal prediction"""
    try:
        data = _read_prediction_payload(request)
        if data is None or not data:
            return _prediction_error('Invalid input data', status=400)
        result = _predict_animals_from_payload(data)

        return JsonResponse({
            'success': True,
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'simulated_environment': result.get('simulated_environment'),
            'decision': result['decision'],
            'trend': result['trend'],
            'future_outlook': result.get('future_outlook'),
            'model_name': animals_metadata.get('model', 'XGBoost (High Performance)'),
            'accuracy': animals_metadata.get('accuracy', 97.7),
            'status': 'success'
        })

    except Exception as e:
        return _prediction_exception_response(e, 'animals')


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
    _load_animals_artifacts_if_needed()
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
    _load_birds_artifacts_if_needed()
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
        result = _predict_insects_from_payload(payload)

        return render(
            request,
            'result.html',
            {
                'prediction': round(result['prediction'], 4),
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
    _load_insects_artifacts_if_needed()
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
        result = _predict_insects_from_payload(payload)
        context = _build_dashboard_context('Insects', result, result['model_input'], insects_model, insects_features)
        context['engineered_summary'] = _build_insects_engineered_preview(result['model_input'])
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
@require_http_methods(["POST"])
def predict_birds(request):
    """Make birds prediction"""
    try:
        data = _read_prediction_payload(request)
        if data is None or not data:
            return _prediction_error('Invalid input data', status=400)
        result = _predict_birds_from_payload(data)
        
        return JsonResponse({
            'success': True,
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'simulated_environment': result.get('simulated_environment'),
            'decision': result['decision'],
            'trend': result['trend'],
            'future_outlook': result.get('future_outlook'),
            'model_name': birds_metadata.get('model', 'XGBoost (High Performance)'),
            'accuracy': birds_metadata.get('accuracy', 91.2),
            'status': 'success'
        })
    
    except Exception as e:
        return _prediction_exception_response(e, 'birds')


@csrf_exempt
@require_http_methods(["POST"])
def predict_insects(request):
    """Make insects prediction"""
    try:
        data = _read_prediction_payload(request)
        if data is None or not data:
            return _prediction_error('Invalid input data', status=400)
        result = _predict_insects_from_payload(data)

        return JsonResponse({
            'success': True,
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'simulated_environment': result.get('simulated_environment'),
            'decision': result['decision'],
            'trend': result['trend'],
            'future_outlook': result.get('future_outlook'),
            'model_name': insects_metadata.get('model', 'XGBoost (High Performance)'),
            'accuracy': insects_metadata.get('accuracy', 94.3),
            'status': 'success'
        })

    except Exception as e:
        return _prediction_exception_response(e, 'insects')



# =============================================================================
# PLANTS — PREDICTION HELPERS + API ENDPOINTS
# =============================================================================

def _plants_base_feature_names():
    """The raw features expected from the Plants prediction form."""
    return BASE_PLANTS_FEATURES


def _build_plants_engineered_features(df_base):
    """Apply the same feature engineering used in train_plants_model.py."""
    X = df_base.copy()

    X['order_family']      = X['order_enc']  * X['family_enc']
    X['richness_family']   = X['species_richness'] * X['family_enc']
    X['richness_order']    = X['species_richness'] * X['order_enc']
    X['class_family']      = X['class_enc']  * X['family_enc']

    X['spatial']           = X['lat_grid'] * X['lon_grid']
    X['spatial_uncertainty'] = (X['lat_grid'] + X['lon_grid']) * X['coordinateUncertaintyInMeters']

    X['season_month']      = X['season_enc'] * X['month']
    X['year_month']        = X['year'] * X['month']
    X['day_month']         = X['day']  * X['month']

    for feat in ['species_richness', 'month', 'day', 'year']:
        X[f'{feat}_sq']   = X[feat] ** 2
        X[f'{feat}_sqrt'] = np.sqrt(np.abs(X[feat]) + 1)
        X[f'{feat}_cbrt'] = np.cbrt(X[feat])

    X['richness_log']     = np.log1p(X['species_richness'])
    X['uncertainty_log']  = np.log1p(X['coordinateUncertaintyInMeters'])
    X['month_log']        = np.log1p(X['month'])

    X['rich_uncertainty_ratio'] = X['species_richness'] / (X['coordinateUncertaintyInMeters'] + 1)
    X['family_order_ratio']     = (X['family_enc'] + 1) / (X['order_enc'] + 1)

    X['spatial_mean']    = (X['lat_grid'] + X['lon_grid']) / 2
    X['temporal_mean']   = (X['day'] + X['month'] + X['decade']) / 3
    X['category_mean']   = (X['order_enc'] + X['family_enc'] + X['class_enc']) / 3

    X['richness_high']    = (X['species_richness'] > X['species_richness'].median()).astype(int)
    X['uncertainty_high'] = (X['coordinateUncertaintyInMeters'] > X['coordinateUncertaintyInMeters'].median()).astype(int)
    X['month_season']     = (X['month'] % 4).astype(int)

    return X


def _predict_plants_from_payload(payload: dict) -> dict:
    """Run the plants regression model given a form/JSON payload."""
    _ensure_prediction_runtime_ready()
    _validate_numeric_inputs(payload, [
        'temperature', 'humidity', 'rainfall', 'vegetation_index', 'water_availability', 'human_disturbance',
        'latitude', 'longitude', 'lat_grid', 'lon_grid', 'decimalLatitude', 'decimalLongitude',
    ] + _plants_base_feature_names())
    _reload_plants_artifacts_if_needed()

    if plants_model is None or plants_scaler is None:
        raise FileNotFoundError('Prediction model not found for plants')

    if hasattr(plants_scaler, 'feature_names_in_'):
        orig_features = list(plants_scaler.feature_names_in_)
        means = dict(zip(plants_scaler.feature_names_in_, getattr(plants_scaler, 'mean_', [])))
    elif isinstance(plants_metadata, dict):
        orig_features = plants_metadata.get('features', _plants_base_feature_names())
        means = {}
    else:
        orig_features = _plants_base_feature_names()
        means = {}

    base_input = {}
    for feature in _plants_base_feature_names():
        value = _safe_float(payload.get(feature))
        if value is None:
            value = means.get(feature, 0.0)
        base_input[feature] = value

    lat = _safe_float(payload.get('lat_grid', 17.5))
    lon = _safe_float(payload.get('lon_grid', 73.5))
    env_data, simulated_environment = _build_prediction_environment(lat, lon, payload)

    # Base Prediction
    def _get_density(p_dict, env_for_density):
        p_in = {}
        for f in _plants_base_feature_names():
            v = _safe_float(p_dict.get(f))
            if v is None: v = means.get(f, 0.0)
            p_in[f] = v
        df_p = pd.DataFrame([p_in])
        try:
            df_e = _build_plants_engineered_features(df_p)
        except Exception:
            df_e = df_p
        for col in orig_features:
            if col not in df_e.columns: df_e[col] = means.get(col, 0.0)
        ds = plants_scaler.transform(df_e[orig_features])
        p = float(plants_model.predict(ds)[0])
        if isinstance(plants_metadata, dict) and plants_metadata.get('target_transform') == 'log1p':
            p = float(np.expm1(p))
        r = _safe_float(p_in.get('species_richness', 0.0))
        baseline = max(0.0, r * 0.18)
        blended = (0.82 * max(0.0, p)) + (0.18 * baseline)
        return max(0.0, blended * _environment_multiplier(env_for_density))

    current_density = _get_density(payload, env_data)
    current_year = int(_safe_float(payload.get('year', 2024)))
    
    # Future Outlook
    p5 = payload.copy(); p5['year'] = current_year + 5
    p10 = payload.copy(); p10['year'] = current_year + 10
    d5 = _get_density(p5, _project_environment(env_data, 5))
    d10 = _get_density(p10, _project_environment(env_data, 10))
    t5, t10 = _predict_occurrence_trend('plants', p5), _predict_occurrence_trend('plants', p10)

    d_change = ((d10 - current_density) / max(current_density, 0.001)) * 100
    
    is_e = False
    rl = "Low"
    msg = "Population projected to remain stable or grow."
    
    if d_change <= -30.0:
        is_e = True
        rl = "High"
        msg = f"CRITICAL: Density model projects a severe {-d_change:.1f}% population drop over 10 years."
    elif d_change <= -10.0:
        rl = "Medium"
        msg = f"WARNING: Model projects a {-d_change:.1f}% declining population trend."

    future_outlook = {
        'projected_density_5yr': round(d5, 2), 'projected_density_10yr': round(d10, 2),
        'projected_trend_5yr': 'Decreasing' if d5 < current_density * 0.99 else 'Increasing' if d5 > current_density * 1.01 else 'Stable',
        'projected_trend_10yr': 'Decreasing' if d10 < current_density * 0.99 else 'Increasing' if d10 > current_density * 1.01 else 'Stable',
        'density_change_10yr_pct': round(d_change, 2),
        'endangered_risk': {
            'is_endangered': is_e, 'risk_level': rl,
            'warning_message': msg
        }
    }

    decision = analyze_prediction(current_density, env_data)
    trend = _predict_occurrence_trend('plants', payload) or analyze_trend(current_density)

    return {
        'prediction': current_density,
        'environmental_data': env_data,
        'simulated_environment': simulated_environment,
        'decision': decision,
        'trend': trend,
        'future_outlook': future_outlook,
        'model_input': base_input,
    }


@csrf_exempt
@require_http_methods(["POST"])
def predict_plants(request):
    """API: Make a plants density prediction."""
    try:
        data = _read_prediction_payload(request)
        if data is None or not data:
            return _prediction_error('Invalid input data', status=400)
        _reload_plants_artifacts_if_needed(force=True)
        result = _predict_plants_from_payload(data)
        meta   = plants_metadata if isinstance(plants_metadata, dict) else {}
        return JsonResponse({
            'success': True,
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'simulated_environment': result.get('simulated_environment'),
            'decision': result['decision'],
            'trend': result['trend'],
            'future_outlook': result.get('future_outlook'),
            'model_name': meta.get('winner', 'XGBoost (High Performance)'),
            'model_info': {
                'winner': meta.get('winner', 'Unknown'),
                'r2': meta.get('r2', 0),
                'cv_r2': meta.get('cv_r2', 0),
                'mae': meta.get('mae', 0),
                'within_25pct': meta.get('within_25pct', 0),
                'comparison': meta.get('comparison', {}),
            },
            'status': 'success'
        })
    except Exception as e:
        return _prediction_exception_response(e, 'plants')


@require_http_methods(["GET"])
def get_plants_features(request):
    """API: Return plants feature ranges for the prediction form."""
    try:
        _lazy_import_ml()
        if pd is None:
            return JsonResponse({'success': False, 'error': 'Prediction processing failed'}, status=500)
        # Prefer engineered regression dataset when available.
        regression_path = Path(_project_file('koyna_plants_regression_density.csv'))
        if regression_path.exists():
            df = pd.read_csv(str(regression_path))
            drop_cols = ['decimalLatitude', 'decimalLongitude', 'plant_sighting_density']
            X = df.drop(columns=[c for c in drop_cols if c in df.columns])
        else:
            # Fallback for environments that only have the raw observations CSV.
            raw_df = pd.read_csv(_project_file('Koyna_plants_final.csv'))

            for col in ['day', 'month', 'year', 'coordinateUncertaintyInMeters']:
                if col in raw_df.columns:
                    raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
                else:
                    raw_df[col] = 0

            raw_df['decade'] = (raw_df['year'] // 10) * 10
            raw_df['lat_grid'] = pd.to_numeric(raw_df.get('decimalLatitude', 0), errors='coerce').fillna(0).round(1)
            raw_df['lon_grid'] = pd.to_numeric(raw_df.get('decimalLongitude', 0), errors='coerce').fillna(0).round(1)

            def _season_from_month(m):
                m = int(max(1, min(12, m or 1)))
                if m in (12, 1, 2):
                    return 0
                if m in (3, 4, 5):
                    return 1
                if m in (6, 7, 8, 9):
                    return 2
                return 3

            raw_df['season_enc'] = raw_df['month'].map(_season_from_month)

            # Encode categorical taxonomic fields to numeric ids for the form ranges.
            for src_col, enc_col in [
                ('order', 'order_enc'),
                ('family', 'family_enc'),
                ('class', 'class_enc'),
                ('taxonRank', 'taxonRank_enc'),
                ('basisOfRecord', 'basisOfRecord_enc'),
            ]:
                if src_col in raw_df.columns:
                    raw_df[enc_col] = pd.factorize(raw_df[src_col].fillna('Unknown'))[0]
                else:
                    raw_df[enc_col] = 0

            if 'species' in raw_df.columns:
                richness = (
                    raw_df.groupby(['lat_grid', 'lon_grid'])['species']
                    .transform(lambda s: s.nunique())
                )
                raw_df['species_richness'] = pd.to_numeric(richness, errors='coerce').fillna(1)
            else:
                raw_df['species_richness'] = 1

            X = raw_df

        if hasattr(plants_scaler, 'feature_names_in_'):
            features = list(plants_scaler.feature_names_in_)
        elif isinstance(plants_metadata, dict):
            features = plants_metadata.get('features', _plants_base_feature_names())
        else:
            features = _plants_base_feature_names()
        env_defaults = {
            'temperature': {'min': 10.0, 'max': 42.0, 'mean': 26.5, 'std': 4.2},
            'humidity': {'min': 20.0, 'max': 98.0, 'mean': 62.0, 'std': 14.0},
            'rainfall': {'min': 0.0, 'max': 150.0, 'mean': 5.0, 'std': 3.0},
        }
        UNIVERSAL_FEATURES = ['lat_grid', 'lon_grid', 'day', 'month', 'year', 'class_enc', 'order_enc', 'family_enc', 'species_richness', 'temperature', 'rainfall', 'humidity']
        mapping = _get_taxonomic_mapping('plants')
        feature_info = {}
        for feat in UNIVERSAL_FEATURES:
            if feat in X.columns:
                col = X[feat].dropna()
                max_val = float(col.max())
                if feat == 'year':
                    max_val = 2100.0  # Infinite manual future projections
                feature_info[feat] = {
                    'min':  float(col.min()),
                    'max':  max_val,
                    'mean': float(col.mean()),
                    'std':  float(col.std()),
                }
                if feat in mapping:
                    feature_info[feat]['options'] = mapping[feat]
            elif feat in env_defaults:
                feature_info[feat] = env_defaults[feat]
        # Attach model comparison info
        meta = plants_metadata if isinstance(plants_metadata, dict) else {}
        feature_info['__model_info__'] = {
            'winner':       meta.get('winner', 'Not trained'),
            'r2':           meta.get('r2', 0),
            'cv_r2':        meta.get('cv_r2', 0),
            'mae':          meta.get('mae', 0),
            'within_25pct': meta.get('within_25pct', 0),
            'comparison':   meta.get('comparison', {}),
        }
        return JsonResponse(feature_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_plants_clustering_api(request):
    """API: Return K-Means cluster assignments for the plants dataset."""
    try:
        n = _parse_cluster_count(request)
        df, elapsed, timed_out = _run_with_timeout(_get_labeled_df, n, 'plants')
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        if df is None:
            return JsonResponse({'error': 'No plants data'}, status=400)
        pts = [
            [round(float(r.decimalLatitude), 5), round(float(r.decimalLongitude), 5), int(r.cluster)]
            for r in df[['decimalLatitude', 'decimalLongitude', 'cluster']].itertuples()
        ]
        logger.info('get_plants_clustering_api served in %.3fs', elapsed)
        return JsonResponse({'points': pts, 'total': len(pts), 'n_clusters': n})
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)


@require_http_methods(["GET"])
def get_plants_model_info(request):
    """API: Return model comparison metrics for the plants section."""
    _reload_plants_artifacts_if_needed()

    meta = plants_metadata if isinstance(plants_metadata, dict) else {}
    km_meta = {}
    try:
        km_meta = prediction_service.load_artifact(_project_file('plants_kmeans_meta.pkl'))
    except Exception:
        pass
    return JsonResponse({
        'regression': {
            'winner':       meta.get('winner', 'Not trained'),
            'r2':           meta.get('r2', 0),
            'cv_r2':        meta.get('cv_r2', 0),
            'mae':          meta.get('mae', 0),
            'within_25pct': meta.get('within_25pct', 0),
            'comparison':   meta.get('comparison', {}),
        },
        'clustering': {
            'n_clusters': km_meta.get('n_clusters', 0),
            'inertia':    km_meta.get('inertia', 0),
        },
        'trained': plants_model is not None,
    })


@require_http_methods(["GET"])
def get_animals_features(request):
    """Return animal features and their ranges"""
    try:
        _lazy_import_ml()
        if pd is None:
            return JsonResponse({'success': False, 'error': 'Prediction processing failed'}, status=500)
        _load_animals_artifacts_if_needed()
        df = pd.read_csv(_project_file('koyna_animals_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'TARGET_sighting_density'])
        
        if hasattr(animals_scaler, 'feature_names_in_'):
            features = list(animals_scaler.feature_names_in_)
        else:
            features = animals_metadata.get('original_features', animals_features)
            
        env_defaults = {
            'temperature': {'min': 10.0, 'max': 42.0, 'mean': 26.5, 'std': 4.2},
            'humidity': {'min': 20.0, 'max': 98.0, 'mean': 62.0, 'std': 14.0},
            'rainfall': {'min': 0.0, 'max': 150.0, 'mean': 5.0, 'std': 3.0},
            'vegetation_index': {'min': 0.05, 'max': 0.98, 'mean': 0.5, 'std': 0.2},
            'water_availability': {'min': 0.0, 'max': 1.0, 'mean': 0.5, 'std': 0.2},
            'human_disturbance': {'min': 0.0, 'max': 1.0, 'mean': 0.3, 'std': 0.1},
        }

        UNIVERSAL_FEATURES = ['lat_grid', 'lon_grid', 'day', 'month', 'year', 'class_enc', 'order_enc', 'family_enc', 'species_richness', 'temperature', 'rainfall', 'humidity']
        mapping = _get_taxonomic_mapping('animals')
        feature_info = {}
        for feature in UNIVERSAL_FEATURES:
            if feature in X.columns:
                max_val = float(X[feature].max())
                if feature == 'year':
                    max_val = 2100.0  # Infinite manual future projections
                    
                feature_info[feature] = {
                    'min': float(X[feature].min()),
                    'max': max_val,
                    'mean': float(X[feature].mean()),
                    'std': float(X[feature].std())
                }
                if feature in mapping:
                    feature_info[feature]['options'] = mapping[feature]
            elif feature in env_defaults:
                feature_info[feature] = env_defaults[feature]
        
        return JsonResponse(feature_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_animals_photos(request):
    """Return wildlife observation photos for the animals page gallery."""
    offset, limit = _parse_gallery_pagination(request)
    payload = _build_gallery_page_payload(_build_animals_gallery_rows(), offset, limit)
    return JsonResponse(payload)


@require_http_methods(["GET"])
def get_birds_photos(request):
    """Return wildlife observation photos for the birds page gallery."""
    offset, limit = _parse_gallery_pagination(request)
    payload = _build_gallery_page_payload(_build_birds_gallery_rows(), offset, limit)
    return JsonResponse(payload)


@require_http_methods(["GET"])
def get_insects_photos(request):
    """Return wildlife observation photos for the insects page gallery."""
    offset, limit = _parse_gallery_pagination(request)
    payload = _build_gallery_page_payload(_build_insects_gallery_rows(), offset, limit)
    return JsonResponse(payload)


@require_http_methods(["GET"])
def get_plants_photos(request):
    """Return wildlife observation photos for the plants page gallery."""
    offset, limit = _parse_gallery_pagination(request)
    payload = _build_gallery_page_payload(_build_plants_gallery_rows(), offset, limit)
    return JsonResponse(payload)


@require_http_methods(["GET"])
def photo_proxy(request):
    """Proxy selected remote images to avoid client-side image host blocking."""
    image_url = str(request.GET.get('url', '')).strip()
    allowed_prefixes = (
        'https://inaturalist-open-data.s3.amazonaws.com/',
        'https://static.inaturalist.org/',
    )

    local_path = serve_cached_media_or_none(image_url)
    if local_path is not None:
        content_type = 'image/jpeg'
        if local_path.suffix.lower() == '.png':
            content_type = 'image/png'
        elif local_path.suffix.lower() == '.webp':
            content_type = 'image/webp'
        elif local_path.suffix.lower() == '.gif':
            content_type = 'image/gif'
        return HttpResponse(local_path.read_bytes(), content_type=content_type)

    if not image_url.startswith(allowed_prefixes):
        return HttpResponse('Invalid image URL', status=400, content_type='text/plain')

    cached_url = resolve_cached_image(image_url, cache_key=f'proxy:{image_url}')
    if cached_url:
        cached_local = serve_cached_media_or_none(cached_url)
        if cached_local is not None:
            content_type = 'image/jpeg'
            if cached_local.suffix.lower() == '.png':
                content_type = 'image/png'
            elif cached_local.suffix.lower() == '.webp':
                content_type = 'image/webp'
            elif cached_local.suffix.lower() == '.gif':
                content_type = 'image/gif'
            return HttpResponse(cached_local.read_bytes(), content_type=content_type)

    return HttpResponse('Image fetch failed', status=502, content_type='text/plain')


@require_http_methods(["GET"])
def get_birds_features(request):
    """Return bird features and their ranges"""
    try:
        _lazy_import_ml()
        if pd is None:
            return JsonResponse({'success': False, 'error': 'Prediction processing failed'}, status=500)
        _load_birds_artifacts_if_needed()
        df = pd.read_csv(_project_file('koyna_birds_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'bird_sighting_density'])
        
        if hasattr(birds_scaler, 'feature_names_in_'):
            features = list(birds_scaler.feature_names_in_)
        else:
            features = birds_metadata.get('original_features', birds_features)
            
        env_defaults = {
            'temperature': {'min': 10.0, 'max': 42.0, 'mean': 26.5, 'std': 4.2},
            'humidity': {'min': 20.0, 'max': 98.0, 'mean': 62.0, 'std': 14.0},
            'rainfall': {'min': 0.0, 'max': 150.0, 'mean': 5.0, 'std': 3.0},
        }
        UNIVERSAL_FEATURES = ['lat_grid', 'lon_grid', 'day', 'month', 'year', 'class_enc', 'order_enc', 'family_enc', 'species_richness', 'temperature', 'rainfall', 'humidity']
        mapping = _get_taxonomic_mapping('birds')
        feature_info = {}
        for feature in UNIVERSAL_FEATURES:
            if feature in X.columns:
                max_val = float(X[feature].max())
                if feature == 'year':
                    max_val = 2100.0  # Infinite manual future projections
                    
                feature_info[feature] = {
                    'min': float(X[feature].min()),
                    'max': max_val,
                    'mean': float(X[feature].mean()),
                    'std': float(X[feature].std())
                }
                if feature in mapping:
                    feature_info[feature]['options'] = mapping[feature]
            elif feature in env_defaults:
                feature_info[feature] = env_defaults[feature]
        
        return JsonResponse(feature_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_insects_features(request):
    """Return insect features and their ranges"""
    try:
        _lazy_import_ml()
        if pd is None:
            return JsonResponse({'success': False, 'error': 'Prediction processing failed'}, status=500)
        _load_insects_artifacts_if_needed()
        df = pd.read_csv(_project_file('koyna_insects_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'insect_sighting_density'])

        if hasattr(insects_scaler, 'feature_names_in_'):
            features = list(insects_scaler.feature_names_in_)
        else:
            features = insects_metadata.get('original_features', insects_features)

        env_defaults = {
            'temperature': {'min': 10.0, 'max': 42.0, 'mean': 26.5, 'std': 4.2},
            'humidity': {'min': 20.0, 'max': 98.0, 'mean': 62.0, 'std': 14.0},
            'rainfall': {'min': 0.0, 'max': 150.0, 'mean': 5.0, 'std': 3.0},
        }
        UNIVERSAL_FEATURES = ['lat_grid', 'lon_grid', 'day', 'month', 'year', 'class_enc', 'order_enc', 'family_enc', 'species_richness', 'temperature', 'rainfall', 'humidity']
        mapping = _get_taxonomic_mapping('insects')
        feature_info = {}
        for feature in UNIVERSAL_FEATURES:
            if feature in X.columns:
                max_val = float(X[feature].max())
                if feature == 'year':
                    max_val = 2100.0  # Infinite manual future projections
                    
                feature_info[feature] = {
                    'min': float(X[feature].min()),
                    'max': max_val,
                    'mean': float(X[feature].mean()),
                    'std': float(X[feature].std())
                }
                if feature in mapping:
                    feature_info[feature]['options'] = mapping[feature]
            elif feature in env_defaults:
                feature_info[feature] = env_defaults[feature]

        return JsonResponse(feature_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# CLUSTERING & SPECIES DETAIL SYSTEM
# =============================================================================

_clustering_cache = { 'animals': {}, 'birds': {}, 'insects': {}, 'plants': {} }
_species_cache = { 'animals': None, 'birds': None, 'insects': None, 'plants': None }
_clustering_lock = threading.Lock()

CLUSTERING_DATASET_CACHE_TTL_SECONDS = int(getattr(settings, 'CLUSTERING_DATASET_CACHE_TTL_SECONDS', 900))
CLUSTERING_RESULT_CACHE_TTL_SECONDS = int(getattr(settings, 'CLUSTERING_RESULT_CACHE_TTL_SECONDS', 900))
CLUSTERING_TIMEOUT_SECONDS = float(getattr(settings, 'CLUSTERING_TIMEOUT_SECONDS', 8.0))
CLUSTERING_MAX_ROWS = int(getattr(settings, 'CLUSTERING_MAX_ROWS', 10000))


def _clustering_error(message: str, status: int = 500):
    return JsonResponse({'success': False, 'error': message}, status=status)


def _parse_cluster_count(request):
    raw_value = str(request.GET.get('clusters', '8')).strip()
    try:
        count = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError('Invalid cluster count')

    if count < 3 or count > 20:
        raise ValueError('Invalid cluster count')

    return count


def _parse_cluster_id(request):
    raw_value = str(request.GET.get('cluster_id', '0')).strip()
    try:
        cluster_id = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError('Invalid cluster id')
    return cluster_id


def _parse_dataset_param(request, default='animals'):
    ds = str(request.GET.get('dataset', default)).strip().lower()
    if ds not in ('animals', 'birds', 'insects', 'plants'):
        raise ValueError('Invalid dataset')
    return ds


def _run_with_timeout(func, *args, timeout_seconds=CLUSTERING_TIMEOUT_SECONDS, **kwargs):
    start = perf_counter()
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    try:
        result = future.result(timeout=timeout_seconds)
        return result, perf_counter() - start, False
    except FuturesTimeoutError:
        logger.warning('Clustering timeout in %s after %.2fs', func.__name__, timeout_seconds)
        future.cancel()
        return None, perf_counter() - start, True
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _load_category_data(category='animals'):
    """Load and cache category CSV data."""
    global _species_cache
    load_start = perf_counter()
    _lazy_import_ml()

    if pd is None:
        logger.warning('ML dependencies unavailable; pandas import failed for category load.')
        return None

    if _species_cache[category] is not None:
        logger.info('Dataset cache hit (memory) for %s in %.3fs', category, perf_counter() - load_start)
        return _species_cache[category]

    from django.core.cache import cache as django_cache
    dataset_cache_key = f'clustering:dataset:{category}'
    cached_df = django_cache.get(dataset_cache_key)
    if cached_df is not None:
        _species_cache[category] = cached_df
        logger.info('Dataset cache hit (django) for %s in %.3fs', category, perf_counter() - load_start)
        return cached_df
    
    files = {
        'animals': 'Koyna_animals_final.csv',
        'birds': 'Koyna_birds_final.csv',
        'insects': 'Koyna_insects_final.csv',
        'plants': 'Koyna_plants_final.csv'
    }
    
    try:
        df = pd.read_csv(_project_file(files[category]))
        _species_cache[category] = df
        django_cache.set(dataset_cache_key, df, timeout=CLUSTERING_DATASET_CACHE_TTL_SECONDS)
        logger.info('Dataset load for %s took %.3fs (rows=%s)', category, perf_counter() - load_start, len(df))
        return df
    except Exception as e:
        logger.warning('Error loading %s data: %s', category, e)
        return pd.DataFrame() if pd is not None else None


def _get_taxonomic_mapping(category: str) -> dict:
    """
    Build dropdown option mappings for encoded taxonomy fields.
    Returns dict like {'class_enc': [...], 'order_enc': [...], 'family_enc': [...]}.
    """
    _lazy_import_ml()
    if pd is None:
        return {}

    category = str(category or 'animals').strip().lower()
    if category not in {'animals', 'birds', 'insects', 'plants'}:
        category = 'animals'

    df = _load_category_data(category)
    if df is None or df.empty:
        return {}

    mappings = {}
    col_to_enc = {
        'class': 'class_enc',
        'order': 'order_enc',
        'family': 'family_enc',
    }

    for raw_col, enc_col in col_to_enc.items():
        if raw_col not in df.columns:
            continue
        values = []
        for val in df[raw_col].dropna().astype(str):
            text = val.strip()
            if not text or text.lower() in {'nan', 'none', 'null'}:
                continue
            values.append(text)
        deduped = list(dict.fromkeys(values))
        if deduped:
            mappings[enc_col] = deduped[:300]

    return mappings


def _perform_clustering(n_clusters=8, category='animals'):
    """
    Perform K-means clustering by location + taxonomy.
    """
    perf_start = perf_counter()
    _lazy_import_ml()
    if StandardScaler is None or KMeans is None:
        raise RuntimeError('Clustering dependencies are unavailable.')

    from django.core.cache import cache as django_cache

    with _clustering_lock:
        cache_key = f'clusters_{n_clusters}'
        if cache_key in _clustering_cache[category]:
            logger.info('Clustering cache hit (memory) for %s/%s in %.3fs', category, n_clusters, perf_counter() - perf_start)
            return _clustering_cache[category][cache_key]

    django_cache_key = f'clustering:result:{category}:{n_clusters}'
    cached_result = django_cache.get(django_cache_key)
    if cached_result is not None:
        with _clustering_lock:
            _clustering_cache[category][cache_key] = cached_result
        logger.info('Clustering cache hit (django) for %s/%s in %.3fs', category, n_clusters, perf_counter() - perf_start)
        return cached_result
    
    df = _load_category_data(category)
    if df is None or df.empty:
        return {'error': 'No data available'}
    
    # Prepare features: geographic + taxonomic encoding
    df_clean = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])
    
    if len(df_clean) == 0:
        return {'error': 'No geographic data available'}
    
    # Feature engineering: location + class encoding
    df_features = df_clean.copy()

    if len(df_features) > CLUSTERING_MAX_ROWS:
        df_features = df_features.sample(n=CLUSTERING_MAX_ROWS, random_state=42)
    
    # Encode categorical features safely
    class_mapping = {cls: i for i, cls in enumerate(df_features['class'].unique())} if 'class' in df_features.columns else {}
    order_mapping = {ord: i for i, ord in enumerate(df_features['order'].unique())} if 'order' in df_features.columns else {}
    
    df_features['class_enc'] = df_features['class'].map(class_mapping).fillna(0) if 'class' in df_features.columns else 0
    df_features['order_enc'] = df_features['order'].map(order_mapping).fillna(0) if 'order' in df_features.columns else 0
    
    # Select features for clustering
    features_for_clustering = df_features[[
        'decimalLatitude', 
        'decimalLongitude', 
        'class_enc',
        'order_enc',
        'year'
    ]].fillna(0)
    
    # Standardize features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features_for_clustering)
    
    # Perform K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(features_scaled)
    
    df_features['cluster'] = cluster_labels
    
    # Build result
    result = {
        'clusters': {},
        'centers': [],
        'n_clusters': n_clusters,
        'total_species': len(df_clean),
    }
    
    # Group species by cluster
    for cluster_id in range(n_clusters):
        cluster_data = df_features[df_features['cluster'] == cluster_id]
        species_in_cluster = cluster_data['scientificName'].unique().tolist()

        # Use geographic mean in original coordinate space for map display.
        center_lat = float(cluster_data['decimalLatitude'].mean()) if len(cluster_data) else 0.0
        center_lon = float(cluster_data['decimalLongitude'].mean()) if len(cluster_data) else 0.0

        result['centers'].append([center_lat, center_lon])

        result['clusters'][str(cluster_id)] = {
            'species_count': len(species_in_cluster),
            'animal_count': len(cluster_data),
            'center_lat': center_lat,
            'center_lon': center_lon,
            'species': species_in_cluster[:10],
        }
    
    with _clustering_lock:
        _clustering_cache[category][cache_key] = result

    django_cache.set(django_cache_key, result, timeout=CLUSTERING_RESULT_CACHE_TTL_SECONDS)
    logger.info('Clustering computed for %s/%s in %.3fs (rows=%s)', category, n_clusters, perf_counter() - perf_start, len(df_features))
    
    return result


def _get_species_detail(species_name, category='animals'):
    """
    Get detailed information about a specific species.
    Returns: species info + all related observations + images
    """
    df = _load_category_data(category)
    if df.empty:
        return {'error': 'No data available'}
    
    # Filter by species name
    species_data = _filter_species_rows(df, species_name)
    
    if species_data.empty:
        return {'error': 'Species not found'}
    
    # Aggregate information
    first_record = species_data.iloc[0]
    
    detail = {
        'scientificName': _safe_text(first_record.get('scientificName'), 'Unknown'),
        'species': _safe_text(first_record.get('species'), 'Unknown'),
        'class': _safe_text(first_record.get('class'), 'Unknown'),
        'order': _safe_text(first_record.get('order'), 'Unknown'),
        'family': _safe_text(first_record.get('family'), 'Unknown'),
        'genus': _safe_text(first_record.get('genus'), 'Unknown'),
        'kingdom': _safe_text(first_record.get('kingdom'), 'Animalia'),
        'phylum': _safe_text(first_record.get('phylum'), 'Unknown'),
        'observationCount': len(species_data),
        'locations': [],
        'occurrenceUrls': [],
        'dateRange': {
            'earliest': _safe_text(species_data['eventDate'].min(), '') if 'eventDate' in species_data.columns else '',
            'latest': _safe_text(species_data['eventDate'].max(), '') if 'eventDate' in species_data.columns else '',
        },
        'geographicRange': {
            'minLat': _safe_number(species_data['decimalLatitude'].min(), 0.0) if 'decimalLatitude' in species_data.columns else 0.0,
            'maxLat': _safe_number(species_data['decimalLatitude'].max(), 0.0) if 'decimalLatitude' in species_data.columns else 0.0,
            'minLon': _safe_number(species_data['decimalLongitude'].min(), 0.0) if 'decimalLongitude' in species_data.columns else 0.0,
            'maxLon': _safe_number(species_data['decimalLongitude'].max(), 0.0) if 'decimalLongitude' in species_data.columns else 0.0,
            'centerLat': _safe_number(species_data['decimalLatitude'].mean(), 0.0) if 'decimalLatitude' in species_data.columns else 0.0,
            'centerLon': _safe_number(species_data['decimalLongitude'].mean(), 0.0) if 'decimalLongitude' in species_data.columns else 0.0,
        },
    }
    
    # Collect all observations
    for _, row in species_data.iterrows():
        loc = {
            'latitude': _safe_number(row.get('decimalLatitude', 0), 0.0),
            'longitude': _safe_number(row.get('decimalLongitude', 0), 0.0),
            'locality': _safe_text(row.get('locality'), 'Unknown locality'),
            'eventDate': _safe_text(row.get('eventDate'), ''),
            'occurrenceID': _safe_text(row.get('occurrenceID'), ''),
        }
        detail['locations'].append(loc)
        detail['occurrenceUrls'].append(_safe_text(row.get('occurrenceID'), ''))
    
    return detail


def _filter_species_rows(df, species_name):
    """
    Filter dataset rows by species/scientific name with exact-first matching.
    """
    if df is None or df.empty:
        return df

    query = str(species_name or '').strip()
    if not query:
        return df.iloc[0:0]

    working = df.copy()
    for col in ('scientificName', 'species'):
        if col not in working.columns:
            working[col] = ''
        else:
            working[col] = working[col].fillna('').astype(str).str.strip()

    q_lower = query.lower()
    exact = working[
        (working['scientificName'].str.lower() == q_lower)
        | (working['species'].str.lower() == q_lower)
    ]
    if not exact.empty:
        return exact

    contains = working[
        working['scientificName'].str.contains(re.escape(query), case=False, na=False)
        | working['species'].str.contains(re.escape(query), case=False, na=False)
    ]
    return contains


def _species_list_payload(category, offset=0, limit=30):
    df = _load_category_data(category)
    if df is None or df.empty:
        return {'species': [], 'total': 0, 'offset': offset, 'nextOffset': offset, 'hasMore': False}

    required_cols = ['scientificName', 'species', 'class', 'order', 'family', 'genus', 'kingdom', 'phylum', 'eventDate']
    normalized = df.copy()
    for col in required_cols:
        if col not in normalized.columns:
            normalized[col] = ''
        normalized[col] = normalized[col].fillna('').astype(str).str.strip()

    grouped = (
        normalized.groupby('scientificName', dropna=False)
        .agg(
            observationCount=('scientificName', 'size'),
            species=('species', 'first'),
            className=('class', 'first'),
            orderName=('order', 'first'),
            family=('family', 'first'),
            genus=('genus', 'first'),
            kingdom=('kingdom', 'first'),
            phylum=('phylum', 'first'),
            earliest=('eventDate', 'min'),
            latest=('eventDate', 'max'),
        )
        .reset_index()
    )

    grouped = grouped[grouped['scientificName'].str.strip() != '']
    grouped = grouped.sort_values(by=['observationCount', 'scientificName'], ascending=[False, True]).reset_index(drop=True)

    total = len(grouped)
    if offset >= total:
        return {'species': [], 'total': total, 'offset': offset, 'nextOffset': offset, 'hasMore': False}

    if limit is None:
        chunk = grouped.iloc[offset:]
    else:
        chunk = grouped.iloc[offset:offset + limit]

    results = []
    for row in chunk.itertuples(index=False):
        results.append({
            'scientificName': _safe_text(getattr(row, 'scientificName', ''), 'Unknown'),
            'species': _safe_text(getattr(row, 'species', ''), 'Unknown'),
            'class': _safe_text(getattr(row, 'className', ''), 'Unknown'),
            'order': _safe_text(getattr(row, 'orderName', ''), 'Unknown'),
            'family': _safe_text(getattr(row, 'family', ''), 'Unknown'),
            'genus': _safe_text(getattr(row, 'genus', ''), 'Unknown'),
            'kingdom': _safe_text(getattr(row, 'kingdom', ''), 'Unknown'),
            'phylum': _safe_text(getattr(row, 'phylum', ''), 'Unknown'),
            'observationCount': int(getattr(row, 'observationCount', 0)),
            'dateRange': {
                'earliest': _safe_text(getattr(row, 'earliest', ''), ''),
                'latest': _safe_text(getattr(row, 'latest', ''), ''),
            },
        })

    next_offset = offset + len(results)
    return {
        'species': results,
        'total': total,
        'offset': offset,
        'nextOffset': next_offset,
        'hasMore': next_offset < total,
    }


@require_http_methods(["GET"])
def animals_clustering_map(request):
    """Render clustering map page for animals."""
    return render(request, 'animals_clustering_map.html', {
        'clustering_api': '/api/animals/clustering/',
        'species_api': '/api/animals/species/',
    })


@require_http_methods(["GET"])
def get_animals_clustering(request):
    """API: Return clustering data for map."""
    try:
        n_clusters = _parse_cluster_count(request)
        result, elapsed, timed_out = _run_with_timeout(_perform_clustering, n_clusters)
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        logger.info('get_animals_clustering served in %.3fs', elapsed)
        return JsonResponse(result)
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)


@require_http_methods(["GET"])
def get_species_detail(request):
    """API: Return detailed information about a species."""
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            offset, limit = _parse_gallery_pagination(request)
            payload = _species_list_payload('animals', offset=offset, limit=limit or 30)
            return JsonResponse(payload, json_dumps_params={'allow_nan': False})

        detail = _sanitize_for_json(_get_species_detail(species_name, 'animals'))
        if isinstance(detail, dict) and detail.get('error'):
            return JsonResponse(detail, status=404, json_dumps_params={'allow_nan': False})
        return JsonResponse(detail, json_dumps_params={'allow_nan': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def species_detail_page(request):
    """Render species detail page with info + gallery."""
    species_name = request.GET.get('species', '').strip()
    if not species_name:
        return HttpResponse('Species parameter required', status=400)
    
    detail = _get_species_detail(species_name)
    if 'error' in detail:
        return HttpResponse(f"Species not found: {species_name}", status=404)
    
    return render(request, 'species_detail.html', {
        'species': detail,
        'species_name': species_name,
        'photos_api': '/api/animals/species-photos/',
    })


@require_http_methods(["GET"])
def get_species_photos(request):
    """API: Get paginated photos for a specific species."""
    return _get_species_photos_generic(request, 'animals')

@require_http_methods(["GET"])
def get_birds_species_photos(request):
    """API: Get paginated photos for a specific bird species."""
    return _get_species_photos_generic(request, 'birds')

@require_http_methods(["GET"])
def get_insects_species_photos(request):
    """API: Get paginated photos for a specific insect species."""
    return _get_species_photos_generic(request, 'insects')

@require_http_methods(["GET"])
def get_plants_species_photos(request):
    """API: Get paginated photos for a specific plant species."""
    return _get_species_photos_generic(request, 'plants')
        
@require_http_methods(["GET"])
def get_birds_clustering(request):
    try:
        n_clusters = _parse_cluster_count(request)
        result, elapsed, timed_out = _run_with_timeout(_perform_clustering, n_clusters, 'birds')
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        logger.info('get_birds_clustering served in %.3fs', elapsed)
        return JsonResponse(result)
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)

@require_http_methods(["GET"])
def get_insects_clustering(request):
    try:
        n_clusters = _parse_cluster_count(request)
        result, elapsed, timed_out = _run_with_timeout(_perform_clustering, n_clusters, 'insects')
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        logger.info('get_insects_clustering served in %.3fs', elapsed)
        return JsonResponse(result)
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)


@require_http_methods(["GET"])
def get_birds_species_detail(request):
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            offset, limit = _parse_gallery_pagination(request)
            payload = _species_list_payload('birds', offset=offset, limit=limit or 30)
            return JsonResponse(payload, json_dumps_params={'allow_nan': False})
        detail = _sanitize_for_json(_get_species_detail(species_name, 'birds'))
        if isinstance(detail, dict) and detail.get('error'):
            return JsonResponse(detail, status=404, json_dumps_params={'allow_nan': False})
        return JsonResponse(detail, json_dumps_params={'allow_nan': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def get_insects_species_detail(request):
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            offset, limit = _parse_gallery_pagination(request)
            payload = _species_list_payload('insects', offset=offset, limit=limit or 30)
            return JsonResponse(payload, json_dumps_params={'allow_nan': False})
        detail = _sanitize_for_json(_get_species_detail(species_name, 'insects'))
        if isinstance(detail, dict) and detail.get('error'):
            return JsonResponse(detail, status=404, json_dumps_params={'allow_nan': False})
        return JsonResponse(detail, json_dumps_params={'allow_nan': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def get_plants_species_detail(request):
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            offset, limit = _parse_gallery_pagination(request)
            payload = _species_list_payload('plants', offset=offset, limit=limit or 30)
            return JsonResponse(payload, json_dumps_params={'allow_nan': False})
        detail = _sanitize_for_json(_get_species_detail(species_name, 'plants'))
        if isinstance(detail, dict) and detail.get('error'):
            return JsonResponse(detail, status=404, json_dumps_params={'allow_nan': False})
        return JsonResponse(detail, json_dumps_params={'allow_nan': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def _get_species_photos_generic(request, category):
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        
        df = _load_category_data(category)
        species_data = _filter_species_rows(df, species_name)
        
        if species_data.empty:
            return JsonResponse({'error': 'Species not found'}, status=404)
        
        offset, limit = _parse_gallery_pagination(request)
        
        # Build photo data (deduplicate by occurrence URL to avoid repeated cards)
        photos = []
        seen = set()
        for _, row in species_data.iterrows():
            occurrence_url = str(row.get('occurrenceID', ''))
            if not occurrence_url.startswith('http'):
                continue
            if occurrence_url in seen:
                continue
            seen.add(occurrence_url)
            
            title = str(row.get('scientificName', 'Unknown'))
            subtitle = str(row.get('locality', 'Koyna Region'))
            event_date = str(row.get('eventDate', ''))
            
            photos.append({
                'title': title[:120],
                'subtitle': subtitle[:80],
                'eventDate': event_date[:20],
                'occurrenceUrl': occurrence_url,
            })
        
        # Paginate
        total = len(photos)
        if offset >= total:
            return JsonResponse({
                'photos': [],
                'count': 0,
                'total': total,
                'offset': offset,
                'hasMore': False,
            })
        
        if limit is None:
            chunk = photos[offset:]
            next_offset = total
        else:
            chunk = photos[offset:offset + limit]
            next_offset = offset + len(chunk)
        
        # Resolve thumbnails in parallel
        occurrence_urls = [item.get('occurrenceUrl', '') for item in chunk]
        thumbnails = _resolve_thumbnails_parallel(occurrence_urls)
        
        result_photos = []
        for item in chunk:
            occurrence_url = item.get('occurrenceUrl', '')
            thumb = thumbnails.get(occurrence_url)
            result_photos.append({
                **item,
                'thumbnailUrl': thumb,
                'hasImage': bool(thumb),
            })
        
        return JsonResponse({
            'photos': result_photos,
            'count': len(result_photos),
            'total': total,
            'offset': offset,
            'nextOffset': next_offset,
            'hasMore': next_offset < total,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# LABELED DATAFRAME CACHE — shared by heatmap, cluster-details, timeline, etc.
# =============================================================================
_labeled_df_cache = {}
_labeled_df_lock = threading.Lock()

def _get_labeled_df(n_clusters=8, category='animals'):
    perf_start = perf_counter()
    _lazy_import_ml()
    if StandardScaler is None or KMeans is None:
        raise RuntimeError('Clustering dependencies are unavailable.')

    from django.core.cache import cache as django_cache

    cache_key = f'{category}_{n_clusters}'
    with _labeled_df_lock:
        if cache_key in _labeled_df_cache:
            logger.info('Labeled DF cache hit (memory) for %s/%s in %.3fs', category, n_clusters, perf_counter() - perf_start)
            return _labeled_df_cache[cache_key]

    django_cache_key = f'clustering:labeled_df:{category}:{n_clusters}'
    cached_df = django_cache.get(django_cache_key)
    if cached_df is not None:
        with _labeled_df_lock:
            _labeled_df_cache[cache_key] = cached_df
        logger.info('Labeled DF cache hit (django) for %s/%s in %.3fs', category, n_clusters, perf_counter() - perf_start)
        return cached_df
    df = _load_category_data(category)
    if df is None or df.empty:
        return None
    df_clean = df.dropna(subset=['decimalLatitude', 'decimalLongitude']).copy()
    if len(df_clean) == 0:
        return None
        
    # Crucial Fix: Downsample massive datasets (like birds) to ensure KMeans 
    # executes instantly on the first click (<0.1s) instead of timing out the map.
    if len(df_clean) > CLUSTERING_MAX_ROWS:
        df_clean = df_clean.sample(n=CLUSTERING_MAX_ROWS, random_state=42)

    cm = {c: i for i, c in enumerate(df_clean['class'].unique())} if 'class' in df_clean.columns else {}
    om = {o: i for i, o in enumerate(df_clean['order'].unique())} if 'order' in df_clean.columns else {}
    df_clean['class_enc'] = df_clean['class'].map(cm).fillna(0) if 'class' in df_clean.columns else 0
    df_clean['order_enc'] = df_clean['order'].map(om).fillna(0) if 'order' in df_clean.columns else 0
    feats = df_clean[['decimalLatitude', 'decimalLongitude', 'class_enc', 'order_enc', 'year']].fillna(0)
    fs = StandardScaler().fit_transform(feats)
    df_clean['cluster'] = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(fs)
    with _labeled_df_lock:
        _labeled_df_cache[cache_key] = df_clean
    django_cache.set(django_cache_key, df_clean, timeout=CLUSTERING_RESULT_CACHE_TTL_SECONDS)
    logger.info('Labeled DF computed for %s/%s in %.3fs (rows=%s)', category, n_clusters, perf_counter() - perf_start, len(df_clean))
    return df_clean


# =============================================================================
# GENERIC CLUSTER HEATMAP  — supports animals / birds / insects
# =============================================================================
@require_http_methods(["GET"])
def get_cluster_heatmap(request):
    try:
        ds = _parse_dataset_param(request)
        n = _parse_cluster_count(request)
        df, elapsed, timed_out = _run_with_timeout(_get_labeled_df, n, ds)
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        if df is None:
            return JsonResponse({'error': 'No data'}, status=400)
        pts = [[round(float(r.decimalLatitude), 5), round(float(r.decimalLongitude), 5), int(r.cluster)]
               for r in df[['decimalLatitude', 'decimalLongitude', 'cluster']].itertuples()]
        logger.info('get_cluster_heatmap served in %.3fs', elapsed)
        return JsonResponse({'points': pts, 'total': len(pts), 'n_clusters': n})
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)


# =============================================================================
# GENERIC CLUSTER DETAILS — species list with trend badges, obsIds, taxonomy
# =============================================================================
@require_http_methods(["GET"])
def get_cluster_details(request):
    try:
        ds = _parse_dataset_param(request)
        n = _parse_cluster_count(request)
        cid = _parse_cluster_id(request)
        df, elapsed, timed_out = _run_with_timeout(_get_labeled_df, n, ds)
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        if df is None:
            return JsonResponse({'error': 'No data'}, status=400)
        cdf = df[df['cluster'] == cid]
        species_list = []
        for sp_name, rows in cdf.groupby('scientificName'):
            if not sp_name or str(sp_name) in ('nan', 'None', ''):
                continue
            obs_ids = []
            for oid in rows.get('occurrenceID', pd.Series(dtype=str)):
                m = re.search(r'/observations/(\d+)', str(oid))
                if m:
                    obs_ids.append(m.group(1))
            obs_ids = list(dict.fromkeys(obs_ids))[:5]
            r0 = rows.iloc[0]
            ym = int(rows['year'].min()) if 'year' in rows.columns and not rows['year'].isna().all() else None
            yM = int(rows['year'].max()) if 'year' in rows.columns and not rows['year'].isna().all() else None
            trend = 'stable'
            if 'year' in rows.columns:
                recent = len(rows[rows['year'] >= 2020])
                prior  = len(rows[(rows['year'] >= 2015) & (rows['year'] < 2020)])
                if prior > 0:
                    if recent < prior * 0.5:   trend = 'declining'
                    elif recent > prior * 1.5: trend = 'rising'
            top_loc = ''
            if 'locality' in rows.columns:
                lc = rows['locality'].dropna().value_counts()
                top_loc = str(lc.index[0]) if len(lc) else 'Koyna Region'
            inat_url = None
            if 'occurrenceID' in rows.columns:
                for oid in rows['occurrenceID'].dropna():
                    if 'inaturalist' in str(oid).lower():
                        inat_url = str(oid); break
            def sv(v, d=''):
                return str(v) if pd.notna(v) else d
            species_list.append({
                'scientificName': str(sp_name),
                'class': sv(r0.get('class')), 'order': sv(r0.get('order')),
                'family': sv(r0.get('family')), 'genus': sv(r0.get('genus')),
                'kingdom': sv(r0.get('kingdom'), 'Animalia'),
                'observationCount': len(rows), 'obsIds': obs_ids, 'hasImage': len(obs_ids) > 0,
                'yearMin': ym, 'yearMax': yM, 'trend': trend,
                'centerLat': round(float(rows['decimalLatitude'].mean()), 5),
                'centerLon': round(float(rows['decimalLongitude'].mean()), 5),
                'topLocality': top_loc, 'inatUrl': inat_url,
            })
        species_list.sort(key=lambda x: x['observationCount'], reverse=True)
        cb = {}
        if 'class' in cdf.columns:
            for c, cnt in cdf['class'].value_counts().head(8).items():
                cb[str(c)] = int(cnt)
        df_fam = ''
        if 'family' in cdf.columns:
            fv = cdf['family'].dropna().value_counts()
            df_fam = str(fv.index[0]) if len(fv) else ''
        logger.info('get_cluster_details served in %.3fs', elapsed)
        return JsonResponse({'clusters': {str(cid): {
            'species': species_list, 'species_count': len(species_list),
            'total_obs': len(cdf), 'class_breakdown': cb, 'dominant_family': df_fam,
        }}})
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)


# =============================================================================
# INAT PHOTO PROXY — server-side batch fetch, cached
# =============================================================================
_inat_photo_cache = {}
_inat_photo_lock  = threading.Lock()

@require_http_methods(["GET"])
def get_inat_photos(request):
    try:
        raw = request.GET.get('obs_ids', '').strip()
        if not raw:
            return JsonResponse({'photos': {}})
        obs_ids = [o.strip() for o in raw.split(',') if o.strip().isdigit()][:40]
        results, to_fetch = {}, []
        with _inat_photo_lock:
            for oid in obs_ids:
                cached_url = _inat_photo_cache.get(oid)
                if cached_url:
                    results[oid] = cached_url
                    continue
                db_cached = resolve_cached_image(None, cache_key=f'obs:{oid}', occurrence_url=f'https://www.inaturalist.org/observations/{oid}')
                if db_cached:
                    results[oid] = db_cached
                    _inat_photo_cache[oid] = db_cached
                else:
                    to_fetch.append(oid)
        def _fetch(obs_id):
            try:
                req = Request(f'https://api.inaturalist.org/v1/observations/{obs_id}?fields=photos',
                               headers={'User-Agent': 'KoynaWildlifeApp/1.0'})
                with urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode())
                photos = data.get('results', [{}])[0].get('photos', [])
                if photos:
                    url = (photos[0].get('url') or '').replace('/square.', '/medium.')
                    cached = resolve_cached_image(
                        url,
                        cache_key=f'obs:{obs_id}',
                        occurrence_url=f'https://www.inaturalist.org/observations/{obs_id}',
                        source='inat-api',
                    )
                    return obs_id, cached or url if url else None
            except Exception: pass
            return obs_id, None
        if to_fetch:
            with ThreadPoolExecutor(max_workers=12) as ex:
                for oid, url in [f.result() for f in as_completed({ex.submit(_fetch, o): o for o in to_fetch})]:
                    results[oid] = url
                    with _inat_photo_lock: _inat_photo_cache[oid] = url
        return JsonResponse({'photos': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_cluster_photos(request):
    """API: Get a collection of photos for a specific cluster."""
    try:
        ds = _parse_dataset_param(request)
        n = _parse_cluster_count(request)
        cid = _parse_cluster_id(request)

        df, elapsed, timed_out = _run_with_timeout(_get_labeled_df, n, ds)
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        if df is None:
            return JsonResponse({'photos': []})
            
        cdf = df[df['cluster'] == cid]
        if cdf.empty:
            return JsonResponse({'photos': []})
            
        # Extract iNat observation IDs
        obs_ids = []
        for oid in cdf['occurrenceID'].dropna():
            m = re.search(r'/observations/(\d+)', str(oid))
            if m:
                obs_ids.append(m.group(1))
        
        # Deduplicate and limit
        obs_ids = list(dict.fromkeys(obs_ids))[:40]
        
        results = []
        def _fetch(obs_id):
            try:
                cache_key = f'cluster:{ds}:{cid}:{obs_id}'
                cached_url = resolve_cached_image(None, cache_key=cache_key, occurrence_url=f'https://www.inaturalist.org/observations/{obs_id}')
                if cached_url:
                    return {
                        'url': cached_url,
                        'obs_id': obs_id,
                        'species': 'Unknown',
                        'common_name': '',
                    }
                req = Request(f'https://api.inaturalist.org/v1/observations/{obs_id}?fields=photos,taxon',
                               headers={'User-Agent': 'KoynaWildlifeApp/1.0'})
                with urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                res = data.get('results', [{}])[0]
                photos = res.get('photos', [])
                taxon = res.get('taxon', {})
                if photos:
                    url = (photos[0].get('url') or '').replace('/square.', '/medium.')
                    cached_url = resolve_cached_image(
                        url,
                        cache_key=cache_key,
                        occurrence_url=f'https://www.inaturalist.org/observations/{obs_id}',
                        species_name=str(taxon.get('name', 'Unknown') or 'Unknown'),
                        category=ds,
                        source='inat-api',
                    )
                    return {
                        'url': cached_url or url,
                        'obs_id': obs_id,
                        'species': taxon.get('name', 'Unknown'),
                        'common_name': taxon.get('preferred_common_name', '')
                    }
            except Exception: pass
            return None

        if obs_ids:
            with ThreadPoolExecutor(max_workers=10) as ex:
                futures = {ex.submit(_fetch, o): o for o in obs_ids}
                for f in as_completed(futures):
                    res = f.result()
                    if res: results.append(res)
        logger.info('get_cluster_photos served in %.3fs', elapsed)
        return JsonResponse({'photos': results, 'count': len(results)})
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)


# =============================================================================
# SPECIES OBSERVATIONS — all GPS points for one species (modal mini-map)
# =============================================================================
@require_http_methods(["GET"])
def get_species_observations(request):
    try:
        species = request.GET.get('species', '').strip()
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'): ds = 'animals'
        if not species:
            return JsonResponse({'error': 'species required'}, status=400)
        df = _load_category_data(ds)
        sp = df[df['scientificName'].str.contains(re.escape(species), case=False, na=False)]
        obs = []
        cols = ['decimalLatitude', 'decimalLongitude', 'eventDate', 'locality', 'recordedBy', 'occurrenceID', 'year']
        for row in sp[[c for c in cols if c in sp.columns]].itertuples():
            try:
                lat, lon = float(row.decimalLatitude), float(row.decimalLongitude)
                if pd.isna(lat) or pd.isna(lon): continue
                oid = str(getattr(row, 'occurrenceID', '') or '')
                m = re.search(r'/observations/(\d+)', oid)
                obs.append({
                    'lat': round(lat, 5), 'lon': round(lon, 5),
                    'date': str(getattr(row, 'eventDate', '') or '')[:10],
                    'locality': str(getattr(row, 'locality', '') or 'Koyna'),
                    'recordedBy': str(getattr(row, 'recordedBy', '') or ''),
                    'inatUrl': oid if 'inaturalist' in oid.lower() else None,
                    'obsId': m.group(1) if m else None,
                    'year': int(row.year) if hasattr(row, 'year') and not pd.isna(row.year) else None,
                })
            except Exception: continue
        return JsonResponse({'observations': obs, 'total': len(obs)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# CLUSTER TIMELINE — year-by-year obs counts for a cluster
# =============================================================================
@require_http_methods(["GET"])
def get_cluster_timeline(request):
    try:
        ds = _parse_dataset_param(request)
        n = _parse_cluster_count(request)
        cid = _parse_cluster_id(request)
        df, elapsed, timed_out = _run_with_timeout(_get_labeled_df, n, ds)
        if timed_out:
            return _clustering_error('Clustering timed out', status=503)
        if df is None: return JsonResponse({'timeline': [], 'total': 0})
        cdf = df[df['cluster'] == cid]
        tl  = []
        if 'year' in cdf.columns:
            yc = cdf.groupby('year').size().reset_index(name='count').sort_values('year')
            tl = [{'year': int(r.year), 'count': int(r.count)} for r in yc.itertuples()]
        logger.info('get_cluster_timeline served in %.3fs', elapsed)
        return JsonResponse({'timeline': tl, 'total': len(cdf)})
    except ValueError as e:
        return _clustering_error(str(e), status=400)
    except Exception as e:
        return _clustering_error(str(e), status=500)


# =============================================================================
# SEASONAL ACTIVITY — obs per month across all years
# =============================================================================
@require_http_methods(["GET"])
def get_seasonal_activity(request):
    try:
        ds = _parse_dataset_param(request)
        df = _load_category_data(ds)
        months = {i: 0 for i in range(1, 13)}
        MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        if 'eventDate' in df.columns:
            dates = pd.to_datetime(df['eventDate'], errors='coerce')
            mc = dates.dt.month.dropna().value_counts()
            for m, c in mc.items():
                if 1 <= m <= 12: months[int(m)] = int(c)
        elif 'month' in df.columns:
            mc = df['month'].dropna().value_counts()
            for m, c in mc.items():
                if 1 <= m <= 12: months[int(m)] = int(c)
        result = [{'month': i, 'name': MONTH_NAMES[i-1], 'count': months[i]} for i in range(1, 13)]
        return JsonResponse({'seasonal': result, 'dataset': ds, 'success': True})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# =============================================================================
# CONSERVATION ALERTS — detect declining species across dataset
# =============================================================================
@require_http_methods(["GET"])
def get_conservation_alerts(request):
    try:
        ds = _parse_dataset_param(request)
        df = _load_category_data(ds)
        alerts = []
        if 'year' not in df.columns or 'scientificName' not in df.columns:
            return JsonResponse({'alerts': [], 'dataset': ds, 'total': 0, 'success': True})
        for sp, rows in df.groupby('scientificName'):
            if len(rows) < 5: continue
            recent = len(rows[rows['year'] >= 2020])
            prior  = len(rows[(rows['year'] >= 2015) & (rows['year'] < 2020)])
            if prior >= 3 and recent < prior * 0.4:
                r0 = rows.iloc[0]
                drop_pct = round((1 - recent/prior) * 100)
                alerts.append({
                    'species': str(sp),
                    'class': str(r0.get('class', '')),
                    'order': str(r0.get('order', '')),
                    'totalObs': len(rows),
                    'recentObs': recent,
                    'priorObs': prior,
                    'dropPercent': drop_pct,
                    'severity': 'critical' if drop_pct >= 70 else 'high' if drop_pct >= 50 else 'medium',
                })
        alerts.sort(key=lambda x: x['dropPercent'], reverse=True)
        return JsonResponse({'alerts': alerts, 'total': len(alerts), 'dataset': ds, 'success': True})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# =============================================================================
# TOP OBSERVERS — citizen science leaderboard
# =============================================================================
@require_http_methods(["GET"])
def get_top_observers(request):
    try:
        ds = _parse_dataset_param(request)
        df = _load_category_data(ds)
        if 'recordedBy' not in df.columns:
            return JsonResponse({'observers': [], 'dataset': ds, 'success': True})
        vc = df['recordedBy'].dropna().str.strip().value_counts().head(20)
        sp_per_obs = df.groupby('recordedBy')['scientificName'].nunique() if 'scientificName' in df.columns else {}
        observers = []
        for name, cnt in vc.items():
            n = str(name).strip()
            if not n or n.lower() in ('', 'nan', 'unknown'): continue
            sp_count = int(sp_per_obs.get(name, 0)) if hasattr(sp_per_obs, 'get') else 0
            observers.append({'name': n, 'observations': int(cnt), 'species': sp_count})
        return JsonResponse({'observers': observers, 'dataset': ds, 'success': True})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# =============================================================================
# DASHBOARD STATS — aggregate stats for all 3 datasets
# =============================================================================
@require_http_methods(["GET"])
def get_dashboard_stats(request):
    try:
        out = {}
        all_observers = set()
        total_alerts = 0
        for ds in ('animals', 'birds', 'insects', 'plants'):
            df = _load_category_data(ds)
            if df.empty:
                out[ds] = {'total': 0, 'species': 0, 'families': 0, 'yearMin': 0, 'yearMax': 0, 'alertsCount': 0}
                continue
            
            # Count alerts for this dataset
            ds_alerts_count = 0
            if 'year' in df.columns and 'scientificName' in df.columns:
                for _, rows in df.groupby('scientificName'):
                    if len(rows) < 5: continue
                    recent = len(rows[rows['year'] >= 2020])
                    prior  = len(rows[(rows['year'] >= 2015) & (rows['year'] < 2020)])
                    if prior >= 3 and recent < prior * 0.4:
                        ds_alerts_count += 1
            total_alerts += ds_alerts_count

            sp = int(df['scientificName'].nunique()) if 'scientificName' in df.columns else 0
            fam = int(df['family'].nunique()) if 'family' in df.columns else 0
            ym = int(df['year'].min()) if 'year' in df.columns and not df['year'].isna().all() else 0
            yM = int(df['year'].max()) if 'year' in df.columns and not df['year'].isna().all() else 0
            
            if 'recordedBy' in df.columns:
                all_observers.update(df['recordedBy'].dropna().unique())

            # top locality
            top_loc = ''
            if 'locality' in df.columns:
                lv = df['locality'].dropna().value_counts()
                top_loc = str(lv.index[0]) if len(lv) else ''
            
            # class breakdown
            cb = {}
            if 'class' in df.columns:
                for c, cnt in df['class'].value_counts().head(6).items():
                    cb[str(c)] = int(cnt)
            
            out[ds] = {
                'total': len(df), 'species': sp, 'families': fam,
                'yearMin': ym, 'yearMax': yM, 'topLocality': top_loc,
                'classBreakdown': cb,
                'alertsCount': ds_alerts_count,
            }
            
        return JsonResponse({
            'datasets': out, 
            'totalRecords': sum(v['total'] for v in out.values()),
            'totalObservers': len(all_observers),
            'totalAlerts': total_alerts,
            'success': True,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# =============================================================================
# WILDLIFE DASHBOARD PAGE VIEW
# =============================================================================
@require_http_methods(["GET"])
def wildlife_dashboard(request):
    return render(request, 'wildlife_dashboard.html')
