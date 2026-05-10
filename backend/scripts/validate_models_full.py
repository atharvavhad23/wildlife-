"""
Validate all trained models by loading and running sample predictions.

Loads each expected artifact from backend/ml_models and runs a sample prediction where applicable.
Prints simple metrics and exits with non-zero code on failures.
"""
from pathlib import Path
import joblib
import logging
import sys
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('validate_models_full')

BASE = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE / 'ml_models'

EXPECTED = [
    'animals_occurrence_classifier.pkl',
    'birds_model.pkl', 'birds_occurrence_classifier.pkl', 'birds_occurrence_features.pkl', 'birds_occurrence_metadata.pkl', 'birds_scaler.pkl',
    'feature_names.pkl',
    'insects_feature_names.pkl', 'insects_model.pkl', 'insects_occurrence_classifier.pkl', 'insects_occurrence_features.pkl', 'insects_occurrence_metadata.pkl', 'insects_scaler.pkl',
    'model_metadata.pkl',
    'plants_feature_names.pkl', 'plants_kmeans.pkl', 'plants_kmeans_meta.pkl', 'plants_kmeans_scaler.pkl', 'plants_metadata.pkl',
    'plants_model.pkl', 'plants_occurrence_classifier.pkl', 'plants_occurrence_features.pkl', 'plants_occurrence_metadata.pkl', 'plants_scaler.pkl',
    'scaler.pkl', 'thumbnail_cache.pkl', 'wildlife_model.pkl',
]

LEGACY_EXPECTED = [
    'animals_model.pkl', 'animals_count_model.pkl', 'animals_feature_names.pkl', 'animals_metadata.pkl', 'birds_feature_names.pkl'
]


def _resolve_feature_names_for_model(model_name):
    """Return feature names from matching feature/metadata artifacts when available."""
    stem = model_name.replace('.pkl', '').replace('.joblib', '')
    family = stem.split('_')[0]
    candidates = []
    for cand in MODEL_DIR.iterdir():
        if not cand.is_file():
            continue
        lname = cand.name.lower()
        if family not in lname and stem not in lname:
            continue
        if 'feature' in lname or 'meta' in lname or 'metadata' in lname:
            candidates.append(cand)
    candidates.sort(key=lambda p: (0 if 'feature' in p.name.lower() else 1, len(p.name)))
    for cand in candidates:
        try:
            payload = joblib.load(cand)
        except Exception:
            continue
        if isinstance(payload, (list, tuple)) and payload:
            return list(payload)
        if isinstance(payload, dict):
            feats = payload.get('features') or payload.get('feature_names') or payload.get('base_features')
            if isinstance(feats, (list, tuple)) and feats:
                return list(feats)
            if isinstance(payload.get('feature_count'), int) and payload['feature_count'] > 0:
                return [f'f{i}' for i in range(int(payload['feature_count']))]
    return None


def _build_sample_input(model_name, obj):
    n = getattr(obj, 'n_features_in_', None)
    if n:
        return np.zeros((1, int(n)))
    feature_names = _resolve_feature_names_for_model(model_name)
    if feature_names:
        return np.zeros((1, len(feature_names)))
    return np.zeros((1, 5))


def _should_predict(name, obj):
    lower = name.lower()
    if lower.endswith('_kmeans.pkl'):
        return hasattr(obj, 'predict')
    if lower.endswith('_model.pkl') or lower.endswith('classifier.pkl'):
        return hasattr(obj, 'predict')
    return False

def load(p):
    try:
        obj = joblib.load(p)
        logger.info(f'OK LOAD: {p} -> {type(obj)}')
        return obj
    except Exception as e:
        logger.exception(f'FAILED LOAD: {p}')
        return None

def run_sample_prediction():
    ok = True
    for name in EXPECTED:
        p = MODEL_DIR / name
        if not p.exists():
            logger.error(f'MISSING: {p}')
            ok = False
            continue
        obj = load(p)
        if obj is None:
            ok = False
            continue
        # sample predict only for actual predictive models
        if _should_predict(name, obj):
            try:
                sample = _build_sample_input(name, obj)
                if hasattr(obj, 'predict_proba'):
                    _ = obj.predict_proba(sample)
                else:
                    _ = obj.predict(sample)
                logger.info(f'SAMPLE PRED OK: {name}')
            except Exception:
                logger.exception(f'SAMPLE PRED FAILED: {name}')
                ok = False
    return ok

def main():
    if not MODEL_DIR.exists():
        logger.error('Model directory missing: ' + str(MODEL_DIR))
        sys.exit(2)
    for name in LEGACY_EXPECTED:
        if not (MODEL_DIR / name).exists():
            logger.warning(f'LEGACY MISSING (not counted as failure): {MODEL_DIR / name}')
    ok = run_sample_prediction()
    if ok:
        logger.info('\nValidation succeeded: all models load and sample predict')
        sys.exit(0)
    else:
        logger.error('\nValidation failed: see errors above')
        sys.exit(1)

if __name__ == '__main__':
    main()
