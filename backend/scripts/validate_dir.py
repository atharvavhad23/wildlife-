"""Validate model artifacts in an arbitrary models directory.

Usage: python validate_dir.py --models-dir <path>
Writes <models-dir>/compatibility_report.json and .csv
"""
from pathlib import Path
import argparse
import json
import csv
import time
import joblib
import numpy as np
import traceback

def _is_helper_file(name: str) -> bool:
    lower = name.lower()
    helpers = (
        'scaler', 'scale', 'standardscaler', 'minmax', 'encoder', 'label', 'labels',
        'meta', 'metadata', 'feature', 'features', 'importance', 'config', 'params',
        'thumbnail_cache', 'cache', 'helper', 'compatibility'
    )
    return any(h in lower for h in helpers)


def _detect_artifact_type(obj, name: str):
    lower = name.lower()
    if any(token in lower for token in ('thumbnail_cache', 'cache', 'helper')):
        return 'helper'
    if isinstance(obj, dict):
        return 'metadata'
    if isinstance(obj, (list, tuple)):
        return 'feature'
    try:
        if isinstance(obj, np.ndarray) and obj.dtype.kind in {'U', 'S', 'O'}:
            return 'feature'
    except Exception:
        pass
    if hasattr(obj, 'transform') and not hasattr(obj, 'predict'):
        return 'scaler'
    if hasattr(obj, 'predict'):
        if any(hasattr(obj, attr) for attr in ('n_clusters', 'cluster_centers_', 'labels_', 'inertia_')):
            return 'clustering'
        if hasattr(obj, 'predict_proba') or hasattr(obj, 'classes_') or getattr(obj, '_estimator_type', None) == 'classifier':
            return 'classifier'
        return 'regressor'
    if _is_helper_file(lower):
        return 'helper'
    return 'unknown'


def _resolve_feature_names(models_dir: Path, model_name: str):
    base = model_name.replace('.pkl', '').replace('.joblib', '')
    candidates = []
    for p in models_dir.iterdir():
        if not p.is_file():
            continue
        name = p.name.lower()
        if 'feature' not in name and 'meta' not in name and 'metadata' not in name:
            continue
        if base.split('_')[0] in name or base in name:
            candidates.append(p)
    # prefer explicit feature-name files, then metadata files
    candidates.sort(key=lambda p: (0 if 'feature' in p.name.lower() else 1, len(p.name)))
    for p in candidates:
        try:
            loaded = joblib.load(p)
            if isinstance(loaded, (list, tuple)) and loaded:
                return list(loaded)
            if isinstance(loaded, dict):
                feats = loaded.get('features') or loaded.get('feature_names') or loaded.get('base_features')
                if isinstance(feats, (list, tuple)) and feats:
                    return list(feats)
                feature_count = loaded.get('feature_count')
                if isinstance(feature_count, int) and feature_count > 0:
                    return [f'f{i}' for i in range(feature_count)]
        except Exception:
            continue
    return None


def _build_sample_input(models_dir: Path, model_name: str, model) -> np.ndarray:
    n_features = getattr(model, 'n_features_in_', None)
    if n_features:
        return np.zeros((1, int(n_features)))
    feat_names = _resolve_feature_names(models_dir, model_name)
    if feat_names:
        return np.zeros((1, len(feat_names)))
    return np.zeros((1, 5))


def _recommendation(entry):
    status = entry.get('status')
    artifact_type = entry.get('type')
    if status == 'PREDICT_OK':
        return 'ready'
    if artifact_type in {'feature', 'metadata', 'scaler', 'helper'}:
        return 'helper-artifact'
    if status in {'LOAD_FAILED', 'ERROR'}:
        return 'fix-load'
    if status == 'PREDICT_FAILED':
        return 'fix-shape-or-compatibility'
    return 'review'


def validate_dir(models_dir: Path):
    out = {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'results': []}
    if not models_dir.exists() or not models_dir.is_dir():
        raise SystemExit(f'models dir not found: {models_dir}')

    for p in sorted(models_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in ('.pkl', '.joblib'):
            continue

        entry = {'file': p.name, 'path': str(p), 'status': 'UNKNOWN', 'error': None, 'has_predict': False, 'has_proba': False, 'n_features_in': None, 'type': None, 'recommendation': None}
        try:
            try:
                model = joblib.load(p)
            except Exception as e:
                entry['status'] = 'LOAD_FAILED'
                entry['error'] = str(e)
                out['results'].append(entry)
                continue

            entry['type'] = _detect_artifact_type(model, p.name)
            entry['has_predict'] = hasattr(model, 'predict')
            entry['has_proba'] = hasattr(model, 'predict_proba')
            entry['n_features_in'] = getattr(model, 'n_features_in_', None)

            if entry['type'] in {'feature', 'metadata', 'scaler', 'helper', 'unknown'}:
                entry['status'] = 'SKIPPED'
            else:
                X = _build_sample_input(models_dir, p.name, model)
                try:
                    if entry['type'] == 'classifier' and hasattr(model, 'predict_proba'):
                        preds = model.predict(X)
                        conf = model.predict_proba(X)
                    else:
                        preds = model.predict(X)
                        conf = None
                    entry['status'] = 'PREDICT_OK'
                    try:
                        entry['sample_prediction'] = preds[0].item() if hasattr(preds[0], 'item') else preds[0]
                    except Exception:
                        entry['sample_prediction'] = str(preds)
                    if conf is not None:
                        try:
                            entry['sample_confidence'] = float(np.max(conf[0])) if hasattr(conf, '__len__') else float(conf)
                        except Exception:
                            entry['sample_confidence'] = str(conf)
                except Exception as e:
                    entry['status'] = 'PREDICT_FAILED'
                    entry['error'] = ''.join(traceback.format_exception_only(type(e), e)).strip()

        except Exception as e:
            entry['status'] = 'ERROR'
            entry['error'] = ''.join(traceback.format_exception_only(type(e), e)).strip()
        entry['recommendation'] = _recommendation(entry)
        out['results'].append(entry)

    jpath = models_dir / 'compatibility_report.json'
    cpath = models_dir / 'compatibility_report.csv'
    jpath.write_text(json.dumps(out, indent=2))
    with open(cpath, 'w', newline='') as fh:
        fieldnames = ['file', 'type', 'status', 'recommendation', 'has_predict', 'has_proba', 'n_features_in', 'sample_prediction', 'sample_confidence', 'error']
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in out['results']:
            writer.writerow({k: r.get(k) for k in fieldnames})

    return jpath, cpath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models-dir', required=True, help='Directory containing model artifacts')
    args = parser.parse_args()
    j, c = validate_dir(Path(args.models_dir))
    print('Wrote', j, 'and', c)


if __name__ == '__main__':
    main()
