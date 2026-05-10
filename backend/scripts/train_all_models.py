"""
Train all wildlife ML models from CSV datasets and save artifacts to backend/ml_models.

Saves:
 - animals_model.pkl (density regressor)
 - animals_count_model.pkl (count regressor)
 - animals_clf.pkl (classification)
 - animals_feature_names.pkl, animals_metadata.pkl, animals_scaler.pkl where appropriate
 - birds_model.pkl, birds_clf.pkl, birds_feature_names.pkl, birds_metadata.pkl, birds_scaler.pkl
 - insects_model.pkl, insects_clf.pkl, insects_feature_names.pkl, insects_metadata.pkl, insects_scaler.pkl
 - plants_model.pkl, plants_kmeans.pkl, plants_feature_names.pkl, plants_metadata.pkl, plants_scaler.pkl, plants_kmeans_scaler.pkl, plants_kmeans_meta.pkl

Do not use any existing incompatible artifacts; this script retrains from CSVs.
"""
from __future__ import annotations

from pathlib import Path
import json
import logging
import sys
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_absolute_error, r2_score

try:
    from xgboost import XGBClassifier, XGBRegressor
    XGB_AVAILABLE = True
except Exception:
    XGB_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('train_all')

BASE = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE / 'ml_models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def detect_target(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    # try heuristic: any column with name containing 'target' or 'class' or 'density' or 'count'
    for col in df.columns:
        lc = col.lower()
        if 'target' in lc or 'density' in lc or 'count' in lc or lc.endswith('_class') or lc == 'class':
            return col
    return None


def prepare_features(df: pd.DataFrame, target_col: str) -> Tuple[pd.DataFrame, pd.Series, list[str], dict]:
    # drop lat/lon and target
    drop = {target_col, 'decimalLatitude', 'decimalLongitude'}
    # determine feature columns
    feature_cols = [c for c in df.columns if c not in drop]
    X = df[feature_cols].copy()
    # simple handling: numeric -> numeric, object -> ordinal encoded
    numeric_cols = []
    cat_cols = []
    for c in X.columns:
        if pd.api.types.is_numeric_dtype(X[c]):
            numeric_cols.append(c)
        else:
            # try convertable
            coerced = pd.to_numeric(X[c], errors='coerce')
            nonnull = coerced.notna().sum()
            if nonnull / max(1, len(coerced)) > 0.9:
                X[c] = coerced.fillna(0.0)
                numeric_cols.append(c)
            else:
                cat_cols.append(c)

    enc = None
    if cat_cols:
        enc = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
        X_cat = X[cat_cols].fillna('missing')
        X[cat_cols] = enc.fit_transform(X_cat)

    # coerce all to numeric and fillna
    X = X.apply(pd.to_numeric, errors='coerce').fillna(0.0)
    y = pd.to_numeric(df[target_col], errors='coerce')
    y = y.fillna(0.0)

    metadata = {
        'features': list(X.columns),
        'numeric_cols': numeric_cols,
        'categorical_cols': cat_cols,
    }
    return X, y, list(X.columns), {'encoder': enc, **metadata}


def fit_classifier(X_train, y_train):
    if XGB_AVAILABLE:
        clf = XGBClassifier(use_label_encoder=False, eval_metric='logloss', n_estimators=200)
    else:
        clf = RandomForestClassifier(n_estimators=200, n_jobs=-1)
    clf.fit(X_train, y_train)
    return clf


def fit_regressor(X_train, y_train):
    if XGB_AVAILABLE:
        reg = XGBRegressor(objective='reg:squarederror', n_estimators=200)
    else:
        reg = RandomForestRegressor(n_estimators=200, n_jobs=-1)
    reg.fit(X_train, y_train)
    return reg


def train_and_save(name: str, df: pd.DataFrame, target_col: str, task: str):
    # task: 'classification' or 'regression'
    X, y, feature_names, prep_meta = prepare_features(df, target_col)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    # scale numeric features for regressors; tree models don't need scaling but we save scaler for compatibility
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    if task == 'classification':
        # ensure labels integer
        y_train_enc = y_train.astype(int)
        y_test_enc = y_test.astype(int)
        clf = fit_classifier(X_train_scaled, y_train_enc)
        preds = clf.predict(X_test_scaled)
        report = classification_report(y_test_enc, preds, output_dict=True, zero_division=0)
        metadata = {
            'model': name,
            'task': 'classification',
            'target': target_col,
            'source_rows': len(df),
            'features': feature_names,
            'classification_report': report,
        }
        model_obj = clf
    else:
        reg = fit_regressor(X_train_scaled, y_train)
        preds = reg.predict(X_test_scaled)
        metadata = {
            'model': name,
            'task': 'regression',
            'target': target_col,
            'source_rows': len(df),
            'features': feature_names,
            'r2': float(r2_score(y_test, preds)),
            'mae': float(mean_absolute_error(y_test, preds)),
        }
        model_obj = reg

    # save artifacts
    model_path = MODEL_DIR / f"{name}.pkl"
    scaler_path = MODEL_DIR / f"{name.replace('_model', '')}_scaler.pkl" if task == 'regression' else MODEL_DIR / f"{name}_scaler.pkl"
    feature_path = MODEL_DIR / f"{name.replace('_model', '')}_feature_names.pkl"
    meta_path = MODEL_DIR / f"{name.replace('_model', '')}_metadata.pkl"

    joblib.dump(model_obj, model_path)
    joblib.dump(scaler, scaler_path)
    joblib.dump(feature_names, feature_path)
    joblib.dump(metadata, meta_path)

    logger.info(f"Saved {model_path}, {scaler_path}, {feature_path}, {meta_path}")

    return model_path


def train_animals():
    # classification
    cls_df = pd.read_csv(DATA_ROOT / 'koyna_animals_classification_class.csv')
    cls_target = detect_target(cls_df, ['TARGET_class', 'class', 'target'])
    if cls_target is not None:
        train_and_save('animals_occurrence_classifier', cls_df, cls_target, 'classification')
    # density regression
    den_df = pd.read_csv(DATA_ROOT / 'koyna_animals_regression_density.csv')
    den_target = detect_target(den_df, ['TARGET_sighting_density', 'sighting_density', 'density'])
    if den_target:
        train_and_save('animals_model', den_df, den_target, 'regression')
    # count regression
    cnt_df = pd.read_csv(DATA_ROOT / 'koyna_animals_regression_count.csv')
    cnt_target = detect_target(cnt_df, ['TARGET_individualCount', 'individualCount', 'count'])
    if cnt_target:
        train_and_save('animals_count_model', cnt_df, cnt_target, 'regression')


def train_birds():
    # classification if available in final
    try:
        cls_df = pd.read_csv(DATA_ROOT / 'koyna_birds_final.csv')
        cls_target = detect_target(cls_df, ['TARGET_class', 'class', 'target'])
        if cls_target:
            train_and_save('birds_occurrence_classifier', cls_df, cls_target, 'classification')
    except FileNotFoundError:
        logger.info('No koyna_birds_final.csv; skipping bird classifier')

    # density
    den_df = pd.read_csv(DATA_ROOT / 'koyna_birds_regression_density.csv')
    den_target = detect_target(den_df, ['bird_sighting_density', 'TARGET_sighting_density', 'density'])
    if den_target:
        train_and_save('birds_model', den_df, den_target, 'regression')


def train_insects():
    try:
        cls_df = pd.read_csv(DATA_ROOT / 'koyna_insects_final.csv')
        cls_target = detect_target(cls_df, ['TARGET_class', 'class', 'target'])
        if cls_target:
            train_and_save('insects_occurrence_classifier', cls_df, cls_target, 'classification')
    except FileNotFoundError:
        logger.info('No koyna_insects_final.csv; skipping insect classifier')

    den_df = pd.read_csv(DATA_ROOT / 'koyna_insects_regression_density.csv')
    den_target = detect_target(den_df, ['insect_sighting_density', 'TARGET_sighting_density', 'density'])
    if den_target:
        train_and_save('insects_model', den_df, den_target, 'regression')


def train_plants():
    # occurrence model from final if there's a class column
    try:
        cls_df = pd.read_csv(DATA_ROOT / 'koyna_plants_final.csv')
        cls_target = detect_target(cls_df, ['TARGET_class', 'class', 'occurrence', 'target'])
        if cls_target:
            train_and_save('plants_occurrence_classifier', cls_df, cls_target, 'classification')
    except FileNotFoundError:
        logger.info('No koyna_plants_final.csv; skipping plants classifier')

    # density regression
    den_df = pd.read_csv(DATA_ROOT / 'koyna_plants_regression_density.csv')
    den_target = detect_target(den_df, ['plant_sighting_density', 'TARGET_sighting_density', 'density'])
    if den_target:
        train_and_save('plants_model', den_df, den_target, 'regression')

    # KMeans clustering
    clustering_df = den_df.copy()
    cluster_features = [c for c in clustering_df.columns if c not in ('decimalLatitude', 'decimalLongitude', den_target)]
    X_cluster = clustering_df[cluster_features].apply(pd.to_numeric, errors='coerce').fillna(0.0)
    kmeans_scaler = StandardScaler()
    X_cluster_scaled = kmeans_scaler.fit_transform(X_cluster)
    kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
    kmeans.fit(X_cluster_scaled)

    joblib.dump(kmeans, MODEL_DIR / 'plants_kmeans.pkl')
    joblib.dump(kmeans_scaler, MODEL_DIR / 'plants_kmeans_scaler.pkl')
    joblib.dump({'n_clusters': 8, 'inertia': float(kmeans.inertia_), 'features': cluster_features}, MODEL_DIR / 'plants_kmeans_meta.pkl')
    logger.info('Saved plants KMeans and meta')


def main():
    train_animals()
    train_birds()
    train_insects()
    train_plants()
    print(json.dumps({'status': 'ok', 'model_dir': str(MODEL_DIR)}))


if __name__ == '__main__':
    main()
