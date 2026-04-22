"""
Core prediction service - handles all prediction logic for all categories.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional

from predictor.services.model_loader import ModelLoader
from predictor.services.preprocessing import safe_float
from predictor.utils.environmental_data import get_environmental_data
from predictor.utils.decision_engine import analyze_prediction
from predictor.utils.trend_analysis import analyze_trend
from predictor.constants.model_features import (
    BASE_BIRDS_FEATURES,
    BASE_INSECTS_FEATURES,
    BASE_ANIMALS_FEATURES,
    BASE_PLANTS_FEATURES,
    BASE_ANIMALS_OCCURRENCE_FEATURES,
)


def get_birds_thresholds() -> Dict[str, float]:
    """Get threshold values for birds engineered features"""
    return {
        'species_richness_median': 25.0,
        'coordinateUncertaintyInMeters_median': 100.0,
    }


def get_insects_thresholds() -> Dict[str, float]:
    """Get threshold values for insects engineered features"""
    return {
        'species_richness_median': 20.0,
        'coordinateUncertaintyInMeters_median': 80.0,
    }


def get_plants_thresholds() -> Dict[str, float]:
    """Get threshold values for plants engineered features"""
    return {
        'species_richness_median': 15.0,
        'coordinateUncertaintyInMeters_median': 120.0,
    }


def get_animals_thresholds() -> Dict[str, float]:
    """Get threshold values for animals engineered features"""
    return {
        'species_richness_median': 30.0,
        'coordinateUncertaintyInMeters_median': 90.0,
    }


def extract_animals_lat_lon(payload: dict) -> tuple:
    """Extract latitude and longitude from animals payload"""
    lat = safe_float(payload.get('lat_grid'), 0.0)
    lon = safe_float(payload.get('lon_grid'), 0.0)
    return lat, lon


def build_birds_engineered_features(df_base: pd.DataFrame) -> pd.DataFrame:
    """Create engineered features for birds model"""
    X = df_base.copy()
    thresholds = get_birds_thresholds()

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

    # Binary features
    X['richness_high'] = (X['species_richness'] > thresholds['species_richness_median']).astype(int)
    X['uncertainty_high'] = (
        X['coordinateUncertaintyInMeters'] > thresholds['coordinateUncertaintyInMeters_median']
    ).astype(int)
    X['month_season'] = (X['month'] % 4).astype(int)

    return X


def build_insects_engineered_features(df_base: pd.DataFrame) -> pd.DataFrame:
    """Create engineered features for insects model"""
    X = df_base.copy()
    thresholds = get_insects_thresholds()

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

    # Binary features
    X['richness_high'] = (X['species_richness'] > thresholds['species_richness_median']).astype(int)
    X['uncertainty_high'] = (
        X['coordinateUncertaintyInMeters'] > thresholds['coordinateUncertaintyInMeters_median']
    ).astype(int)
    X['month_season'] = (X['month'] % 4).astype(int)

    return X


def build_plants_engineered_features(df_base: pd.DataFrame) -> pd.DataFrame:
    """Create engineered features for plants model"""
    X = df_base.copy()
    thresholds = get_plants_thresholds()

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

    # Binary features
    X['richness_high'] = (X['species_richness'] > thresholds['species_richness_median']).astype(int)
    X['uncertainty_high'] = (
        X['coordinateUncertaintyInMeters'] > thresholds['coordinateUncertaintyInMeters_median']
    ).astype(int)
    X['month_season'] = (X['month'] % 4).astype(int)

    return X


def predict_animals(payload: dict) -> Dict:
    """
    Predict animals density/count.
    
    Args:
        payload: Request payload with all required features
        
    Returns:
        Prediction result dict with prediction, environmental_data, decision, trend
        
    Raises:
        ValueError: If models not loaded or required features missing
    """
    model = ModelLoader.load_model('animals')
    scaler = ModelLoader.load_scaler('animals')
    
    if model is None or scaler is None:
        raise ValueError('Animals model artifacts are not loaded.')

    lat, lon = extract_animals_lat_lon(payload)
    env_data = get_environmental_data(lat, lon)

    model_input = {}
    for feature in BASE_ANIMALS_FEATURES:
        user_value = safe_float(payload.get(feature))
        if user_value is not None:
            model_input[feature] = user_value
            continue

        if feature in env_data:
            model_input[feature] = float(env_data[feature])
            continue

        raise ValueError(f'Missing feature: {feature}')

    df_input = pd.DataFrame([model_input])
    df_scaled = scaler.transform(df_input)
    prediction = float(model.predict(df_scaled)[0])
    
    # Handle log transform if needed
    metadata = ModelLoader.load_metadata('animals')
    if isinstance(metadata, dict) and metadata.get('target_transform') == 'log1p':
        prediction = float(np.expm1(prediction))
    
    decision = analyze_prediction(prediction, env_data)
    trend = predict_occurrence_trend('animals', model_input) or analyze_trend(prediction)

    return {
        'prediction': prediction,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': model_input,
    }


def predict_birds(payload: dict) -> Dict:
    """
    Predict bird species density.
    
    Args:
        payload: Request payload with all required features
        
    Returns:
        Prediction result dict
        
    Raises:
        ValueError: If models not loaded or required features missing
    """
    model = ModelLoader.load_model('birds')
    scaler = ModelLoader.load_scaler('birds')
    features = ModelLoader.load_feature_names('birds')
    metadata = ModelLoader.load_metadata('birds')
    
    if model is None or scaler is None:
        raise ValueError('Bird prediction model is currently unavailable. Please retry shortly.')

    base_input = {}
    for feature in BASE_BIRDS_FEATURES:
        value = safe_float(payload.get(feature))
        if value is None:
            raise ValueError(f'Missing feature: {feature}')
        base_input[feature] = value

    df_base = pd.DataFrame([base_input])
    df_engineered = build_birds_engineered_features(df_base)

    missing = [f for f in features if f not in df_engineered.columns]
    if missing:
        msg = f"Model expects engineered features not available: {missing[:5]}"
        if len(missing) > 5:
            msg += "..."
        raise ValueError(msg)

    df_input = df_engineered[features]
    df_scaled = scaler.transform(df_input)
    pred = float(model.predict(df_scaled)[0])

    if isinstance(metadata, dict) and metadata.get('target_transform') == 'log1p':
        pred = float(np.expm1(pred))

    env_data = get_environmental_data(base_input['lat_grid'], base_input['lon_grid'])
    decision = analyze_prediction(pred, env_data)
    trend = predict_occurrence_trend('birds', base_input) or analyze_trend(pred)

    return {
        'prediction': pred,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': base_input,
    }


def predict_insects(payload: dict) -> Dict:
    """
    Predict insect species density.
    
    Args:
        payload: Request payload with all required features
        
    Returns:
        Prediction result dict
        
    Raises:
        ValueError: If models not loaded or required features missing
    """
    model = ModelLoader.load_model('insects')
    scaler = ModelLoader.load_scaler('insects')
    features = ModelLoader.load_feature_names('insects')
    metadata = ModelLoader.load_metadata('insects')
    
    if model is None or scaler is None:
        raise ValueError('Insect prediction model is currently unavailable. Please retry shortly.')

    base_input = {}
    for feature in BASE_INSECTS_FEATURES:
        value = safe_float(payload.get(feature))
        if value is None:
            raise ValueError(f'Missing feature: {feature}')
        base_input[feature] = value

    df_base = pd.DataFrame([base_input])
    df_engineered = build_insects_engineered_features(df_base)

    missing = [f for f in features if f not in df_engineered.columns]
    if missing:
        msg = f"Model expects engineered features not available: {missing[:5]}"
        if len(missing) > 5:
            msg += "..."
        raise ValueError(msg)

    df_input = df_engineered[features]
    df_scaled = scaler.transform(df_input)
    pred = float(model.predict(df_scaled)[0])

    if isinstance(metadata, dict) and metadata.get('target_transform') == 'log1p':
        pred = float(np.expm1(pred))

    env_data = get_environmental_data(base_input['lat_grid'], base_input['lon_grid'])
    decision = analyze_prediction(pred, env_data)
    trend = predict_occurrence_trend('insects', base_input) or analyze_trend(pred)

    return {
        'prediction': pred,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': base_input,
    }


def predict_plants(payload: dict) -> Dict:
    """
    Predict plant species density.
    
    Args:
        payload: Request payload with all required features
        
    Returns:
        Prediction result dict
        
    Raises:
        ValueError: If models not loaded or required features missing
    """
    model = ModelLoader.load_model('plants')
    scaler = ModelLoader.load_scaler('plants')
    features = ModelLoader.load_feature_names('plants')
    metadata = ModelLoader.load_metadata('plants')
    
    if model is None or scaler is None:
        raise ValueError(
            'Plants model not yet trained. '
            'Run: python prepare_plants_data.py && python train_plants_model.py'
        )

    base_input = {}
    for feature in BASE_PLANTS_FEATURES:
        value = safe_float(payload.get(feature))
        if value is None:
            raise ValueError(f'Missing feature: {feature}')
        base_input[feature] = value

    df_base = pd.DataFrame([base_input])
    df_engineered = build_plants_engineered_features(df_base)

    # Use only the features the model was trained on
    feature_cols = features if isinstance(features, list) else BASE_PLANTS_FEATURES
    available = [f for f in feature_cols if f in df_engineered.columns]
    df_input = df_engineered[available]

    df_scaled = scaler.transform(df_input)
    pred = float(model.predict(df_scaled)[0])

    if isinstance(metadata, dict) and metadata.get('target_transform') == 'log1p':
        pred = float(np.expm1(pred))

    env_data = get_environmental_data(base_input['lat_grid'], base_input['lon_grid'])
    decision = analyze_prediction(pred, env_data)
    trend = predict_occurrence_trend('plants', base_input) or analyze_trend(pred)

    return {
        'prediction': pred,
        'environmental_data': env_data,
        'decision': decision,
        'trend': trend,
        'model_input': base_input,
    }


def predict_occurrence_trend(category: str, feature_values: dict) -> Optional[dict]:
    """
    Predict occurrence trend class using RandomForestClassifier.
    
    Args:
        category: Category name (animals/birds/insects/plants)
        feature_values: Dict of feature values
        
    Returns:
        Trend dict or None if classifier not available
    """
    model = ModelLoader.load_occurrence_classifier(category)
    if model is None:
        return None

    features = ModelLoader.load_occurrence_features(category)
    if not features:
        return None

    row = []
    for feat in features:
        val = safe_float(feature_values.get(feat), 0.0)
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
            'label': trend_label,
            'percentage_change': pct,
            'confidence': confidence,
        }
    except Exception:
        return None
