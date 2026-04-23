from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import joblib
import pandas as pd
import numpy as np
import math
import json
import re
import secrets
from urllib.parse import quote_plus
from urllib.request import urlopen, Request
import warnings
from pathlib import Path
from predictor.utils.environmental_data import get_environmental_data
from predictor.utils.decision_engine import analyze_prediction
from predictor.utils.trend_analysis import analyze_trend
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pickle
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

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
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    email = str(payload.get('email', '')).strip().lower()
    purpose = str(payload.get('purpose', 'auth')).strip().lower() or 'auth'

    # ✅ Validate email
    if not email or '@' not in email:
        return JsonResponse({'error': 'Valid email is required.'}, status=400)

    # ✅ Proper SMTP configuration check (FIXED)
    if not all([
        getattr(settings, 'EMAIL_HOST', ''),
        getattr(settings, 'EMAIL_HOST_USER', ''),
        getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    ]):
        return JsonResponse(
            {'error': 'SMTP configuration incomplete. Check EMAIL_HOST, USER, PASSWORD.'},
            status=400,
        )

    # ✅ Generate OTP
    otp = f"{secrets.randbelow(900000) + 100000}"

    # ✅ Store OTP in cache
    cache.set(_otp_key(email, purpose), otp, timeout=OTP_TTL_SECONDS)
    cache.delete(_otp_verified_key(email, purpose))

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
        print("EMAIL ERROR:", exc)  # Debug in terminal
        return JsonResponse(
            {'error': f'Failed to send OTP email: {str(exc)}'},
            status=500
        )

    return JsonResponse({'status': 'success', 'message': 'OTP sent to email.'})


@csrf_exempt
@require_http_methods(["POST"])
def verify_email_otp(request):
    """Verify OTP code sent to email."""
    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        payload = {}

    email = str(payload.get('email', '')).strip().lower()
    purpose = str(payload.get('purpose', 'auth')).strip().lower() or 'auth'
    code = str(payload.get('otp', '')).strip()

    if not email or '@' not in email:
        return JsonResponse({'error': 'Valid email is required.'}, status=400)
    if not code:
        return JsonResponse({'error': 'OTP code is required.'}, status=400)

    stored = cache.get(_otp_key(email, purpose))
    if stored is None:
        return JsonResponse({'error': 'OTP expired or not found. Request a new code.'}, status=400)

    if str(stored) != code:
        return JsonResponse({'error': 'Invalid OTP code.'}, status=400)

    cache.set(_otp_verified_key(email, purpose), True, timeout=15 * 60)
    cache.delete(_otp_key(email, purpose))

    return JsonResponse({'status': 'success', 'verified': True})


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
        occurrence_models[category] = joblib.load(_project_file(f'{category}_occurrence_classifier.pkl'))
        try:
            loaded_features = joblib.load(_project_file(f'{category}_occurrence_features.pkl'))
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


def _normalize_species_text(value: str) -> str:
    text = _safe_text(value, '').lower().strip()
    return re.sub(r'\s+', ' ', text)


def _species_core_name(value: str) -> str:
    """Strip author/year suffix patterns to improve species matching."""
    text = _normalize_species_text(value)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = text.split(',')[0].strip()
    return re.sub(r'\s+', ' ', text)


def _filter_species_rows(df: pd.DataFrame, species_name: str) -> pd.DataFrame:
    """Find species rows robustly across naming variants and author suffixes."""
    if df.empty or 'scientificName' not in df.columns:
        return pd.DataFrame()

    query = _normalize_species_text(species_name)
    if not query:
        return pd.DataFrame()

    sci = df['scientificName'].fillna('').astype(str)
    norm = sci.map(_normalize_species_text)

    # 1) Exact normalized match.
    exact = df[norm == query]
    if not exact.empty:
        return exact

    # 2) Literal contains (no regex interpretation of special chars).
    literal = df[sci.str.contains(species_name, case=False, na=False, regex=False)]
    if not literal.empty:
        return literal

    # 3) Match by core species name without author/year text.
    query_core = _species_core_name(species_name)
    if query_core:
        norm_core = norm.map(_species_core_name)
        core = df[(norm_core == query_core) | norm_core.str.startswith(query_core + ' ', na=False)]
        if not core.empty:
            return core

        core_literal = df[sci.str.contains(query_core, case=False, na=False, regex=False)]
        if not core_literal.empty:
            return core_literal

    return pd.DataFrame()


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
    trend = _predict_occurrence_trend('animals', model_input) or analyze_trend(prediction)

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
    trend = _predict_occurrence_trend('birds', base_input) or analyze_trend(pred)

    return {
        'prediction': pred,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': base_input,
    }


def _predict_insects_from_payload(payload: dict) -> dict:
    if insects_model is None or insects_scaler is None:
        raise ValueError('Insect prediction model is currently unavailable. Please retry shortly.')

    base_input = {}
    for feature in _insects_base_feature_names():
        value = _safe_float(payload.get(feature))
        if value is None:
            raise ValueError(f'Missing feature: {feature}')
        base_input[feature] = value

    df_base = pd.DataFrame([base_input])
    df_engineered = _build_insects_engineered_features(df_base)

    missing = [f for f in insects_features if f not in df_engineered.columns]
    if missing:
        msg = f"Model expects engineered features not available: {missing[:5]}"
        if len(missing) > 5:
            msg += "..."
        raise ValueError(msg)

    df_input = df_engineered[insects_features]
    df_scaled = insects_scaler.transform(df_input)
    pred = float(insects_model.predict(df_scaled)[0])

    if isinstance(insects_metadata, dict) and insects_metadata.get('target_transform') == 'log1p':
        pred = float(np.expm1(pred))

    env_data = get_environmental_data(base_input['lat_grid'], base_input['lon_grid'])
    decision = analyze_prediction(pred, env_data)
    trend = _predict_occurrence_trend('insects', base_input) or analyze_trend(pred)

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


# Load insects artifacts
insects_model = None
insects_scaler = None
insects_features = BASE_INSECTS_FEATURES.copy()
insects_metadata = {}

try:
    try:
        insects_features = joblib.load(_project_file('insects_feature_names.pkl'))
    except Exception:
        insects_features = BASE_INSECTS_FEATURES.copy()

    insects_scaler = joblib.load(_project_file('insects_scaler.pkl'))
    insects_model = joblib.load(_project_file('insects_model.pkl'))
    try:
        insects_metadata = joblib.load(_project_file('insects_metadata.pkl'))
    except Exception:
        insects_metadata = {}
    print("Insects model loaded successfully.")
except Exception as e:
    print(f"Error loading insects model: {e}")


# Load plants artifacts
plants_model = None
plants_scaler = None
plants_features = BASE_PLANTS_FEATURES.copy()
plants_metadata = {}
plants_kmeans = None
plants_kmeans_scaler = None

try:
    try:
        plants_features = joblib.load(_project_file('plants_feature_names.pkl'))
    except Exception:
        plants_features = BASE_PLANTS_FEATURES.copy()

    plants_scaler = joblib.load(_project_file('plants_scaler.pkl'))
    plants_model  = joblib.load(_project_file('plants_model.pkl'))
    try:
        plants_metadata = joblib.load(_project_file('plants_metadata.pkl'))
    except Exception:
        plants_metadata = {}
    try:
        plants_kmeans        = joblib.load(_project_file('plants_kmeans.pkl'))
        plants_kmeans_scaler = joblib.load(_project_file('plants_kmeans_scaler.pkl'))
    except Exception:
        plants_kmeans = None
    print("Plants model loaded successfully.")
except Exception as e:
    print(f"Plants model not yet trained ({e}). Run: python prepare_plants_data.py && python train_plants_model.py")


def _reload_plants_artifacts_if_needed(force: bool = False):
    """Load plants model artifacts on demand if they were unavailable at startup."""
    global plants_model, plants_scaler, plants_features, plants_metadata, plants_kmeans, plants_kmeans_scaler

    if not force and plants_model is not None and plants_scaler is not None:
        return

    try:
        try:
            plants_features = joblib.load(_project_file('plants_feature_names.pkl'))
        except Exception:
            plants_features = BASE_PLANTS_FEATURES.copy()

        plants_scaler = joblib.load(_project_file('plants_scaler.pkl'))
        plants_model = joblib.load(_project_file('plants_model.pkl'))

        try:
            plants_metadata = joblib.load(_project_file('plants_metadata.pkl'))
        except Exception:
            plants_metadata = {}

        try:
            plants_kmeans = joblib.load(_project_file('plants_kmeans.pkl'))
            plants_kmeans_scaler = joblib.load(_project_file('plants_kmeans_scaler.pkl'))
        except Exception:
            plants_kmeans = None
            plants_kmeans_scaler = None
    except Exception:
        # Keep existing values; caller will handle untrained state.
        pass



_birds_thresholds_cache = None
_insects_thresholds_cache = None
_oembed_cache = {}  # In-memory cache (session-scoped)
_gallery_rows_cache = {}
_thumbnail_executor = ThreadPoolExecutor(max_workers=6)  # Parallel thumbnail resolver
_cache_lock = threading.Lock()  # Thread-safe cache access
_persistent_cache_path = Path(__file__).resolve().parent.parent / 'thumbnail_cache.pkl'

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
        cached = _oembed_cache.get(occurrence_url)
        if cached is not None:
            return cached

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

    with _cache_lock:
        _oembed_cache[occurrence_url] = thumbnail_url
    
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


def _build_insects_engineered_features(df_base: pd.DataFrame) -> pd.DataFrame:
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
    """Render the home page with both options"""
    return render(request, 'home.html')


def animals_prediction(request):
    """Render animals prediction page"""
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
        data = json.loads(request.body)
        result = _predict_animals_from_payload(data)

        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'model_name': _model_display_name(animals_model, 'RandomForestRegressor'),
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
        data = json.loads(request.body)
        result = _predict_birds_from_payload(data)
        
        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'model_name': _model_display_name(birds_model, 'Regression Model'),
            'status': 'success'
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def predict_insects(request):
    """Make insects prediction"""
    try:
        data = json.loads(request.body)
        result = _predict_insects_from_payload(data)

        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'model_name': _model_display_name(insects_model, 'Regression Model'),
            'status': 'success'
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)



# =============================================================================
# PLANTS — PREDICTION HELPERS + API ENDPOINTS
# =============================================================================

def _plants_base_feature_names():
    """The raw features expected from the Plants prediction form."""
    return BASE_PLANTS_FEATURES


def _build_plants_engineered_features(df_base: pd.DataFrame) -> pd.DataFrame:
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
    _reload_plants_artifacts_if_needed()

    if plants_model is None or plants_scaler is None:
        raise ValueError(
            'Plants model not yet trained. '
            'Run: python prepare_plants_data.py && python train_plants_model.py'
        )

    base_input = {}
    for feature in _plants_base_feature_names():
        value = _safe_float(payload.get(feature))
        if value is None:
            raise ValueError(f'Missing feature: {feature}')
        base_input[feature] = value

    df_base       = pd.DataFrame([base_input])
    df_engineered = _build_plants_engineered_features(df_base)

    # Use only the features the model was trained on
    feature_cols = plants_features if isinstance(plants_features, list) else _plants_base_feature_names()
    available    = [f for f in feature_cols if f in df_engineered.columns]
    df_input     = df_engineered[available]

    df_scaled    = plants_scaler.transform(df_input)
    pred         = float(plants_model.predict(df_scaled)[0])

    if isinstance(plants_metadata, dict) and plants_metadata.get('target_transform') == 'log1p':
        pred = float(np.expm1(pred))

    env_data = get_environmental_data(base_input['lat_grid'], base_input['lon_grid'])
    decision = analyze_prediction(pred, env_data)
    trend = _predict_occurrence_trend('plants', base_input) or analyze_trend(pred)

    return {
        'prediction': pred,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': base_input,
    }


@csrf_exempt
@require_http_methods(["POST"])
def predict_plants(request):
    """API: Make a plants density prediction."""
    try:
        data   = json.loads(request.body)
        result = _predict_plants_from_payload(data)
        meta   = plants_metadata if isinstance(plants_metadata, dict) else {}
        return JsonResponse({
            'prediction': result['prediction'],
            'environmental_data': result['environmental_data'],
            'decision': result['decision'],
            'trend': result['trend'],
            'model_name': _model_display_name(plants_model, 'Regression Model'),
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
        return JsonResponse({'error': str(e), 'status': 'error'}, status=400)


@require_http_methods(["GET"])
def get_plants_features(request):
    """API: Return plants feature ranges for the prediction form."""
    try:
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

        feature_info = {}
        for feat in _plants_base_feature_names():
            if feat in X.columns:
                col = X[feat].dropna()
                feature_info[feat] = {
                    'min':  float(col.min()),
                    'max':  float(col.max()),
                    'mean': float(col.mean()),
                    'std':  float(col.std()),
                }
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
        n = max(3, min(20, int(request.GET.get('clusters', 8))))
        df = _get_labeled_df(n, 'plants')
        if df is None:
            return JsonResponse({'error': 'No plants data'}, status=400)
        pts = [
            [round(float(r.decimalLatitude), 5), round(float(r.decimalLongitude), 5), int(r.cluster)]
            for r in df[['decimalLatitude', 'decimalLongitude', 'cluster']].itertuples()
        ]
        return JsonResponse({'points': pts, 'total': len(pts), 'n_clusters': n})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_plants_model_info(request):
    """API: Return model comparison metrics for the plants section."""
    _reload_plants_artifacts_if_needed()

    meta = plants_metadata if isinstance(plants_metadata, dict) else {}
    km_meta = {}
    try:
        km_meta = joblib.load(_project_file('plants_kmeans_meta.pkl'))
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

    if not image_url.startswith(allowed_prefixes):
        return HttpResponse('Invalid image URL', status=400, content_type='text/plain')

    try:
        req = Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as response:
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            data = response.read()
        return HttpResponse(data, content_type=content_type)
    except Exception:
        return HttpResponse('Image fetch failed', status=502, content_type='text/plain')


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


@require_http_methods(["GET"])
def get_insects_features(request):
    """Return insect features and their ranges"""
    try:
        df = pd.read_csv(_project_file('koyna_insects_regression_density.csv'))
        X = df.drop(columns=['decimalLatitude', 'decimalLongitude', 'insect_sighting_density'])

        feature_info = {}
        for feature in _insects_base_feature_names():
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


# =============================================================================
# CLUSTERING & SPECIES DETAIL SYSTEM
# =============================================================================

_clustering_cache = { 'animals': {}, 'birds': {}, 'insects': {}, 'plants': {} }
_species_cache = { 'animals': None, 'birds': None, 'insects': None, 'plants': None }
_clustering_lock = threading.Lock()


def _load_category_data(category='animals'):
    """Load and cache category CSV data."""
    global _species_cache
    if _species_cache[category] is not None:
        return _species_cache[category]
    
    files = {
        'animals': 'Koyna_animals_final.csv',
        'birds': 'Koyna_birds_final.csv',
        'insects': 'Koyna_insects_final.csv',
        'plants': 'Koyna_plants_final.csv'
    }
    
    try:
        df = pd.read_csv(_project_file(files[category]))
        _species_cache[category] = df
        return df
    except Exception as e:
        print(f"Error loading {category} data: {e}")
        return pd.DataFrame()


def _perform_clustering(n_clusters=8, category='animals'):
    """
    Perform K-means clustering by location + taxonomy.
    """
    with _clustering_lock:
        cache_key = f'clusters_{n_clusters}'
        if cache_key in _clustering_cache[category]:
            return _clustering_cache[category][cache_key]
    
    df = _load_category_data(category)
    if df.empty:
        return {'error': 'No data available'}
    
    # Prepare features: geographic + taxonomic encoding
    df_clean = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])
    
    if len(df_clean) == 0:
        return {'error': 'No geographic data available'}
    
    # Feature engineering: location + class encoding
    df_features = df_clean.copy()
    
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
        n_clusters = int(request.GET.get('clusters', 8))
        n_clusters = max(3, min(20, n_clusters))
        
        result = _perform_clustering(n_clusters)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_species_detail(request):
    """API: Return detailed information about a species."""
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        
        detail = _sanitize_for_json(_get_species_detail(species_name))
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
        n_clusters = int(request.GET.get('clusters', 8))
        n_clusters = max(3, min(20, n_clusters))
        result = _perform_clustering(n_clusters, 'birds')
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def get_insects_clustering(request):
    try:
        n_clusters = int(request.GET.get('clusters', 8))
        n_clusters = max(3, min(20, n_clusters))
        result = _perform_clustering(n_clusters, 'insects')
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_birds_species_detail(request):
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        detail = _sanitize_for_json(_get_species_detail(species_name, 'birds'))
        return JsonResponse(detail, json_dumps_params={'allow_nan': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def get_insects_species_detail(request):
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        detail = _sanitize_for_json(_get_species_detail(species_name, 'insects'))
        return JsonResponse(detail, json_dumps_params={'allow_nan': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def get_plants_species_detail(request):
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        detail = _sanitize_for_json(_get_species_detail(species_name, 'plants'))
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
        
        # Build photo data
        photos = []
        for _, row in species_data.iterrows():
            occurrence_url = str(row.get('occurrenceID', ''))
            if not occurrence_url.startswith('http'):
                continue
            
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
    cache_key = f'{category}_{n_clusters}'
    with _labeled_df_lock:
        if cache_key in _labeled_df_cache:
            return _labeled_df_cache[cache_key]
    df = _load_category_data(category)
    if df.empty:
        return None
    df_clean = df.dropna(subset=['decimalLatitude', 'decimalLongitude']).copy()
    if len(df_clean) == 0:
        return None
    cm = {c: i for i, c in enumerate(df_clean['class'].unique())} if 'class' in df_clean.columns else {}
    om = {o: i for i, o in enumerate(df_clean['order'].unique())} if 'order' in df_clean.columns else {}
    df_clean['class_enc'] = df_clean['class'].map(cm).fillna(0) if 'class' in df_clean.columns else 0
    df_clean['order_enc'] = df_clean['order'].map(om).fillna(0) if 'order' in df_clean.columns else 0
    feats = df_clean[['decimalLatitude', 'decimalLongitude', 'class_enc', 'order_enc', 'year']].fillna(0)
    fs = StandardScaler().fit_transform(feats)
    df_clean['cluster'] = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(fs)
    with _labeled_df_lock:
        _labeled_df_cache[cache_key] = df_clean
    return df_clean


# =============================================================================
# GENERIC CLUSTER HEATMAP  — supports animals / birds / insects
# =============================================================================
@require_http_methods(["GET"])
def get_cluster_heatmap(request):
    try:
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'):
            ds = 'animals'
        n = max(3, min(20, int(request.GET.get('clusters', 8))))
        df = _get_labeled_df(n, ds)
        if df is None:
            return JsonResponse({'error': 'No data'}, status=400)
        pts = [[round(float(r.decimalLatitude), 5), round(float(r.decimalLongitude), 5), int(r.cluster)]
               for r in df[['decimalLatitude', 'decimalLongitude', 'cluster']].itertuples()]
        return JsonResponse({'points': pts, 'total': len(pts), 'n_clusters': n})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# GENERIC CLUSTER DETAILS — species list with trend badges, obsIds, taxonomy
# =============================================================================
@require_http_methods(["GET"])
def get_cluster_details(request):
    try:
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'):
            ds = 'animals'
        n = max(3, min(20, int(request.GET.get('clusters', 8))))
        cid = int(request.GET.get('cluster_id', 0))
        df = _get_labeled_df(n, ds)
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
        return JsonResponse({'clusters': {str(cid): {
            'species': species_list, 'species_count': len(species_list),
            'total_obs': len(cdf), 'class_breakdown': cb, 'dominant_family': df_fam,
        }}})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


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
                if oid in _inat_photo_cache: results[oid] = _inat_photo_cache[oid]
                else: to_fetch.append(oid)
        def _fetch(obs_id):
            try:
                req = Request(f'https://api.inaturalist.org/v1/observations/{obs_id}?fields=photos',
                               headers={'User-Agent': 'KoynaWildlifeApp/1.0'})
                with urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode())
                photos = data.get('results', [{}])[0].get('photos', [])
                if photos:
                    url = (photos[0].get('url') or '').replace('/square.', '/medium.')
                    return obs_id, url if url else None
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
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'): ds = 'animals'
        n = max(3, min(20, int(request.GET.get('clusters', 8))))
        cid = int(request.GET.get('cluster_id', 0))
        
        df = _get_labeled_df(n, ds)
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
                req = Request(f'https://api.inaturalist.org/v1/observations/{obs_id}?fields=photos,taxon',
                               headers={'User-Agent': 'KoynaWildlifeApp/1.0'})
                with urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                res = data.get('results', [{}])[0]
                photos = res.get('photos', [])
                taxon = res.get('taxon', {})
                if photos:
                    url = (photos[0].get('url') or '').replace('/square.', '/medium.')
                    return {
                        'url': url,
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
        
        return JsonResponse({'photos': results, 'count': len(results)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


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
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'): ds = 'animals'
        n   = max(3, min(20, int(request.GET.get('clusters', 8))))
        cid = int(request.GET.get('cluster_id', 0))
        df  = _get_labeled_df(n, ds)
        if df is None: return JsonResponse({'timeline': [], 'total': 0})
        cdf = df[df['cluster'] == cid]
        tl  = []
        if 'year' in cdf.columns:
            yc = cdf.groupby('year').size().reset_index(name='count').sort_values('year')
            tl = [{'year': int(r.year), 'count': int(r.count)} for r in yc.itertuples()]
        return JsonResponse({'timeline': tl, 'total': len(cdf)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# SEASONAL ACTIVITY — obs per month across all years
# =============================================================================
@require_http_methods(["GET"])
def get_seasonal_activity(request):
    try:
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'): ds = 'animals'
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
        return JsonResponse({'seasonal': result, 'dataset': ds})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# CONSERVATION ALERTS — detect declining species across dataset
# =============================================================================
@require_http_methods(["GET"])
def get_conservation_alerts(request):
    try:
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'): ds = 'animals'
        df = _load_category_data(ds)
        alerts = []
        if 'year' not in df.columns or 'scientificName' not in df.columns:
            return JsonResponse({'alerts': []})
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
        return JsonResponse({'alerts': alerts[:30], 'total': len(alerts), 'dataset': ds})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# TOP OBSERVERS — citizen science leaderboard
# =============================================================================
@require_http_methods(["GET"])
def get_top_observers(request):
    try:
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects', 'plants'): ds = 'animals'
        df = _load_category_data(ds)
        if 'recordedBy' not in df.columns:
            return JsonResponse({'observers': []})
        vc = df['recordedBy'].dropna().str.strip().value_counts().head(20)
        sp_per_obs = df.groupby('recordedBy')['scientificName'].nunique() if 'scientificName' in df.columns else {}
        observers = []
        for name, cnt in vc.items():
            n = str(name).strip()
            if not n or n.lower() in ('', 'nan', 'unknown'): continue
            sp_count = int(sp_per_obs.get(name, 0)) if hasattr(sp_per_obs, 'get') else 0
            observers.append({'name': n, 'observations': int(cnt), 'species': sp_count})
        return JsonResponse({'observers': observers, 'dataset': ds})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# DASHBOARD STATS — aggregate stats for all 3 datasets
# =============================================================================
@require_http_methods(["GET"])
def get_dashboard_stats(request):
    try:
        out = {}
        all_observers = set()
        for ds in ('animals', 'birds', 'insects', 'plants'):
            df = _load_category_data(ds)
            if df.empty:
                out[ds] = {'total': 0, 'species': 0, 'families': 0, 'yearMin': 0, 'yearMax': 0}
                continue
            
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
            }
            
        return JsonResponse({
            'datasets': out, 
            'totalRecords': sum(v['total'] for v in out.values()),
            'totalObservers': len(all_observers)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# WILDLIFE DASHBOARD PAGE VIEW
# =============================================================================
@require_http_methods(["GET"])
def wildlife_dashboard(request):
    return render(request, 'wildlife_dashboard.html')
