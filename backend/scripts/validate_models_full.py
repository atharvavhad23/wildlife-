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
    'animals_model.pkl', 'animals_count_model.pkl', 'animals_occurrence_classifier.pkl',
    'animals_feature_names.pkl', 'animals_metadata.pkl',
    'birds_model.pkl', 'birds_occurrence_classifier.pkl', 'birds_feature_names.pkl', 'birds_metadata.pkl', 'birds_scaler.pkl',
    'insects_model.pkl', 'insects_occurrence_classifier.pkl', 'insects_feature_names.pkl', 'insects_metadata.pkl', 'insects_scaler.pkl',
    'plants_model.pkl', 'plants_occurrence_classifier.pkl', 'plants_feature_names.pkl', 'plants_metadata.pkl', 'plants_scaler.pkl',
    'plants_kmeans.pkl', 'plants_kmeans_meta.pkl', 'plants_kmeans_scaler.pkl',
]

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
        # sample predict
        if name.endswith('_model.pkl') or name.endswith('classifier.pkl'):
            try:
                # build a dummy vector from feature count if available
                # find the best-matching feature file by longest common prefix with model filename
                model_basename = name
                candidates = [cand for cand in MODEL_DIR.iterdir() if 'feature' in cand.name.lower()]
                feature_file = None
                best_score = -1
                for cand in candidates:
                    # score by common prefix length
                    a = model_basename.lower()
                    b = cand.name.lower()
                    # compute common prefix length
                    score = 0
                    for ca, cb in zip(a, b):
                        if ca == cb:
                            score += 1
                        else:
                            break
                    if score > best_score:
                        best_score = score
                        feature_file = cand
                if feature_file and feature_file.exists():
                    try:
                        features = joblib.load(feature_file)
                    except Exception:
                        features = None
                    # features may be list or model if mis-matched; guard
                    if isinstance(features, (list, tuple)):
                        n = max(1, len(features))
                    else:
                        n = 5
                else:
                    n = 5
                sample = np.zeros((1, n))
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
    ok = run_sample_prediction()
    if ok:
        logger.info('\nValidation succeeded: all models load and sample predict')
        sys.exit(0)
    else:
        logger.error('\nValidation failed: see errors above')
        sys.exit(1)

if __name__ == '__main__':
    main()
