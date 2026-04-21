from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import joblib
import pandas as pd
import numpy as np
import json
import re
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

_animals_clustering_cache = {}
_animals_species_cache = None
_clustering_lock = threading.Lock()


def _load_animals_data():
    """Load and cache animals CSV data."""
    global _animals_species_cache
    if _animals_species_cache is not None:
        return _animals_species_cache
    
    try:
        df = pd.read_csv(_project_file('Koyna_animals_final.csv'))
        _animals_species_cache = df
        return df
    except Exception:
        return pd.DataFrame()


def _perform_clustering(n_clusters=8):
    """
    Perform K-means clustering on animals by location + taxonomy.
    Returns: {cluster_id: [species_list], centers: [[lat, lon]], ...}
    """
    with _clustering_lock:
        cache_key = f'clusters_{n_clusters}'
        if cache_key in _animals_clustering_cache:
            return _animals_clustering_cache[cache_key]
    
    df = _load_animals_data()
    if df.empty:
        return {'error': 'No data available'}
    
    # Prepare features: geographic + taxonomic encoding
    df_clean = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])
    
    if len(df_clean) == 0:
        return {'error': 'No geographic data available'}
    
    # Feature engineering: location + class encoding
    df_features = df_clean.copy()
    
    # Encode categorical features
    class_mapping = {cls: i for i, cls in enumerate(df_features['class'].unique())}
    order_mapping = {ord: i for i, ord in enumerate(df_features['order'].unique())}
    
    df_features['class_enc'] = df_features['class'].map(class_mapping).fillna(0)
    df_features['order_enc'] = df_features['order'].map(order_mapping).fillna(0)
    
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
        'centers': kmeans.cluster_centers_.tolist(),
        'n_clusters': n_clusters,
        'total_species': len(df_clean),
    }
    
    # Group species by cluster
    for cluster_id in range(n_clusters):
        cluster_data = df_features[df_features['cluster'] == cluster_id]
        species_in_cluster = cluster_data['scientificName'].unique().tolist()
        result['clusters'][str(cluster_id)] = {
            'species_count': len(species_in_cluster),
            'animal_count': len(cluster_data),
            'center_lat': float(kmeans.cluster_centers_[cluster_id][0]),
            'center_lon': float(kmeans.cluster_centers_[cluster_id][1]),
            'species': species_in_cluster[:10],
        }
    
    with _clustering_lock:
        _animals_clustering_cache[cache_key] = result
    
    return result


def _get_species_detail(species_name):
    """
    Get detailed information about a specific species.
    Returns: species info + all related observations + images
    """
    df = _load_animals_data()
    if df.empty:
        return {'error': 'No data available'}
    
    # Filter by species name
    species_data = df[df['scientificName'].str.contains(species_name, case=False, na=False)]
    
    if species_data.empty:
        return {'error': 'Species not found'}
    
    # Aggregate information
    first_record = species_data.iloc[0]
    
    detail = {
        'scientificName': first_record.get('scientificName', 'Unknown'),
        'species': first_record.get('species', 'Unknown'),
        'class': first_record.get('class', 'Unknown'),
        'order': first_record.get('order', 'Unknown'),
        'family': first_record.get('family', 'Unknown'),
        'genus': first_record.get('genus', 'Unknown'),
        'kingdom': first_record.get('kingdom', 'Animalia'),
        'phylum': first_record.get('phylum', 'Unknown'),
        'observationCount': len(species_data),
        'locations': [],
        'occurrenceUrls': [],
        'dateRange': {
            'earliest': species_data['eventDate'].min() if 'eventDate' in species_data.columns else '',
            'latest': species_data['eventDate'].max() if 'eventDate' in species_data.columns else '',
        },
        'geographicRange': {
            'minLat': float(species_data['decimalLatitude'].min()) if 'decimalLatitude' in species_data.columns else 0,
            'maxLat': float(species_data['decimalLatitude'].max()) if 'decimalLatitude' in species_data.columns else 0,
            'minLon': float(species_data['decimalLongitude'].min()) if 'decimalLongitude' in species_data.columns else 0,
            'maxLon': float(species_data['decimalLongitude'].max()) if 'decimalLongitude' in species_data.columns else 0,
            'centerLat': float(species_data['decimalLatitude'].mean()) if 'decimalLatitude' in species_data.columns else 0,
            'centerLon': float(species_data['decimalLongitude'].mean()) if 'decimalLongitude' in species_data.columns else 0,
        },
    }
    
    # Collect all observations
    for _, row in species_data.iterrows():
        loc = {
            'latitude': float(row.get('decimalLatitude', 0)),
            'longitude': float(row.get('decimalLongitude', 0)),
            'locality': str(row.get('locality', 'Unknown')),
            'eventDate': str(row.get('eventDate', '')),
            'occurrenceID': str(row.get('occurrenceID', '')),
        }
        detail['locations'].append(loc)
        detail['occurrenceUrls'].append(str(row.get('occurrenceID', '')))
    
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
        
        detail = _get_species_detail(species_name)
        return JsonResponse(detail)
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
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        
        df = _load_animals_data()
        species_data = df[df['scientificName'].str.contains(species_name, case=False, na=False)]
        
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
