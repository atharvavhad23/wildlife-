"""Professional ML artifact validator for a models directory.

Usage:
  python validate_models_proper.py --models-dir <path>

Writes: <models-dir>/validation_report.json and validation_report.csv
"""
from pathlib import Path
import argparse
import json
import csv
import time
import joblib
import traceback
import numpy as np
import pandas as pd
from math import sqrt

from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, accuracy_score, precision_recall_fscore_support
from sklearn.base import is_classifier, is_regressor
import sklearn
try:
    import xgboost
except Exception:
    xgboost = None
import warnings
warnings.filterwarnings('ignore')


def safe_load(path: Path):
    try:
        return joblib.load(path), None
    except Exception as e:
        return None, str(e)


def detect_artifact_type(obj, name: str):
    lower = name.lower()

    if any(token in lower for token in ('thumbnail_cache', 'cache', 'helper')):
        return 'helper'

    # 1) Type-based detection (rely on the loaded object first)
    try:
        if isinstance(obj, dict):
            return 'metadata'
        if isinstance(obj, (list, tuple)):
            return 'feature'
        # numpy arrays of strings are feature lists
        import numpy as _np
        if isinstance(obj, _np.ndarray) and obj.dtype.type is _np.str_:
            return 'feature'
    except Exception:
        pass

    # scaler-like: has transform but NOT a predict method
    try:
        if hasattr(obj, 'transform') and not hasattr(obj, 'predict'):
            return 'scaler'
    except Exception:
        pass

    # predictive estimators: only if they implement predict
    try:
        if hasattr(obj, 'predict'):
            # clustering detectors
            if any(hasattr(obj, a) for a in ('n_clusters', 'cluster_centers_', 'labels_', 'inertia_')):
                return 'clustering'

            # Try sklearn's utilities when available
            try:
                if is_classifier(obj):
                    return 'classifier'
                if is_regressor(obj):
                    return 'regressor'
            except Exception:
                pass

            # Fallback heuristics for classifiers
            if hasattr(obj, 'predict_proba') or hasattr(obj, 'classes_') or getattr(obj, '_estimator_type', None) == 'classifier':
                return 'classifier'

            # Fallback heuristics for regressors
            if getattr(obj, '_estimator_type', None) == 'regressor' or hasattr(obj, 'coef_') or hasattr(obj, 'feature_importances_'):
                return 'regressor'

            # default: treat as regressor if it predicts numeric outputs on a small sample
            return 'regressor'
    except Exception:
        pass

    # 2) Filename-based heuristics (fallback)
    if lower.endswith(('.pkl', '.joblib')):
        if '_feature' in lower or lower.endswith('_features.pkl') or lower.endswith('_feature_names.pkl') or 'feature_names' in lower:
            return 'feature'
        if '_metadata' in lower or lower.endswith('_meta.pkl') or lower.endswith('_metadata.pkl') or 'meta' in lower:
            return 'metadata'
        if '_scaler' in lower or 'scaler' in lower:
            return 'scaler'
        if 'kmeans' in lower or 'cluster' in lower or 'kmeans' in lower:
            return 'clustering'
        if 'classifier' in lower or 'occurrence' in lower or '_class' in lower or 'classification' in lower:
            return 'classifier_candidate'
        if 'model' in lower or 'regress' in lower or 'predict' in lower:
            return 'regressor_candidate'

    return 'unknown'


def find_feature_names(models_dir: Path, model_name: str):
    # try exact match, then token match
    candidates = []
    base = model_name.replace('.pkl', '')
    names = [f for f in models_dir.iterdir() if f.is_file()]
    for p in names:
        if p.name.lower().startswith(base) and ('feature' in p.name.lower() or 'feature_names' in p.name.lower()):
            candidates.append(p)
    if candidates:
        return candidates[0]
    # token match
    token = base.split('_')[0]
    for p in names:
        if token in p.name.lower() and ('feature' in p.name.lower() or 'feature_names' in p.name.lower()):
            return p
    return None


def check_environment_compatibility():
    compat = {'sklearn': {'version': sklearn.__version__, 'status': 'unknown'},
              'xgboost': {'version': getattr(xgboost, '__version__', None), 'status': 'unknown'}}
    # simple rules
    try:
        sv = tuple(int(x) for x in sklearn.__version__.split('.')[:2])
        if sv >= (1, 0):
            compat['sklearn']['status'] = 'safe'
        else:
            compat['sklearn']['status'] = 'warning'
    except Exception:
        compat['sklearn']['status'] = 'unknown'
    if xgboost is None:
        compat['xgboost']['status'] = 'not_installed'
    else:
        try:
            xv = tuple(int(x) for x in xgboost.__version__.split('.')[:2])
            if xv >= (1, 6):
                compat['xgboost']['status'] = 'safe'
            else:
                compat['xgboost']['status'] = 'warning'
        except Exception:
            compat['xgboost']['status'] = 'unknown'
    return compat


def scan_backend_references(models_dir: Path):
    """Scan common backend files for explicit model references and check existence."""
    base = Path(__file__).resolve().parents[2]
    checks = {'referenced_files': [], 'missing': [], 'duplicates': []}
    # look for prediction_service and other common loaders
    candidates = [base / 'apps' / 'common' / 'prediction_service.py']
    seen = {}
    for f in candidates:
        try:
            if not f.exists():
                continue
            txt = f.read_text()
            # crude extraction: any '.pkl' or '.joblib' in the file
            import re
            for m in re.finditer(r"[\w\-/_\\]+\.(?:pkl|joblib)", txt):
                fn = Path(m.group(0)).name
                checks['referenced_files'].append(fn)
                seen[fn] = seen.get(fn, 0) + 1
                # verify existence under models_dir
                if not any((models_dir / fn).exists() for _ in (0,)):
                    # check direct path
                    if not (base / fn).exists():
                        checks['missing'].append(fn)
        except Exception:
            pass
    # duplicates
    for k, v in seen.items():
        if v > 1:
            checks['duplicates'].append(k)
    return checks


def build_sample_input(models_dir: Path, model_name: str, n_features=None):
    fpath = find_feature_names(models_dir, model_name)
    if fpath:
        try:
            feat, err = safe_load(fpath)
            if feat and isinstance(feat, (list, tuple)):
                n = len(feat)
                X = np.zeros((2, n))
                return X, list(feat)
        except Exception:
            pass
    # fallback to using n_features or default 5
    n = int(n_features) if n_features else 5
    return np.zeros((2, n)), None


def validate_regressor(obj, models_dir: Path, model_name: str):
    report = {'type': 'regressor', 'status': 'OK', 'issues': []}
    n_features = getattr(obj, 'n_features_in_', None)
    X, feat_names = build_sample_input(models_dir, model_name, n_features)
    # test predict
    try:
        preds = obj.predict(X)
        report['sample_prediction'] = float(np.asarray(preds).ravel()[0]) if preds is not None else None
    except Exception as e:
        report['status'] = 'PREDICT_FAILED'
        report['issues'].append(str(e))
        return report

    # optional dataset metrics if available
    # try find matching regression csv
    token = model_name.split('_')[0]
    ds = None
    for p in Path(__file__).resolve().parents[2].iterdir():
        if p.suffix == '.csv' and token in p.name.lower() and 'regression' in p.name.lower():
            ds = p
            break
    if ds:
        try:
            df = pd.read_csv(ds)
            # try detect target
            target = None
            for t in ['TARGET_sighting_density','sighting_density','TARGET_individualCount','individualCount','bird_sighting_density','insect_sighting_density','plant_sighting_density']:
                if t in df.columns:
                    target = t
                    break
            if target is not None and feat_names:
                Xfull = df[feat_names].apply(pd.to_numeric, errors='coerce').fillna(0.0).values
                y = pd.to_numeric(df[target], errors='coerce').fillna(0.0)
                try:
                    ypred = obj.predict(Xfull)
                    report.update({
                        'r2': float(r2_score(y, ypred)),
                        'rmse': float(sqrt(mean_squared_error(y, ypred))),
                        'mae': float(mean_absolute_error(y, ypred))
                    })
                except Exception as e:
                    report['issues'].append('dataset_metrics_failed:' + str(e))
        except Exception:
            pass

    return report


def validate_classifier(obj, models_dir: Path, model_name: str):
    report = {'type': 'classifier', 'status': 'OK', 'issues': []}
    n_features = getattr(obj, 'n_features_in_', None)
    X, feat_names = build_sample_input(models_dir, model_name, n_features)
    try:
        preds = obj.predict(X)
        report['sample_prediction'] = preds[0].tolist() if hasattr(preds[0], 'tolist') else preds[0]
    except Exception as e:
        report['status'] = 'PREDICT_FAILED'
        report['issues'].append(str(e))
        return report

    if hasattr(obj, 'predict_proba'):
        try:
            probs = obj.predict_proba(X)
            report['predict_proba_ok'] = True
        except Exception as e:
            report['predict_proba_ok'] = False
            report['issues'].append('predict_proba_failed:' + str(e))

    # dataset metrics if available
    token = model_name.split('_')[0]
    ds = None
    for p in Path(__file__).resolve().parents[2].iterdir():
        if p.suffix == '.csv' and token in p.name.lower() and ('class' in p.name.lower() or 'final' in p.name.lower() or 'classification' in p.name.lower()):
            ds = p
            break
    if ds and feat_names:
        try:
            df = pd.read_csv(ds)
            # detect target
            target = None
            for t in ['TARGET_class','class','occurrence','presence']:
                if t in df.columns:
                    target = t
                    break
            if target:
                Xfull = df[feat_names].apply(pd.to_numeric, errors='coerce').fillna(0.0).values
                y = df[target]
                try:
                    ypred = obj.predict(Xfull)
                    acc = float(accuracy_score(y, ypred))
                    prec, rec, f1, _ = precision_recall_fscore_support(y, ypred, average='weighted', zero_division=0)
                    report.update({'accuracy': acc, 'precision': float(prec), 'recall': float(rec), 'f1': float(f1)})
                except Exception as e:
                    report['issues'].append('dataset_metrics_failed:' + str(e))
        except Exception:
            pass

    return report


def validate_clustering(obj, models_dir: Path, model_name: str):
    report = {'type': 'clustering', 'status': 'OK', 'issues': []}
    # check n_clusters and inertia
    try:
        report['n_clusters'] = int(getattr(obj, 'n_clusters', getattr(obj, 'n_clusters_', None) or 0))
    except Exception:
        report['n_clusters'] = None
    try:
        report['inertia'] = float(getattr(obj, 'inertia_', None) or getattr(obj, 'inertia', None) or 0.0)
    except Exception:
        report['inertia'] = None

    # silhouette on dataset if possible
    token = model_name.split('_')[0]
    ds = None
    for p in Path(__file__).resolve().parents[2].iterdir():
        if p.suffix == '.csv' and token in p.name.lower() and 'plants' in p.name.lower():
            ds = p
            break
    if ds:
        try:
            df = pd.read_csv(ds)
            featp = find_feature_names(models_dir, model_name)
            if featp:
                feats = joblib.load(featp)
                X = df[feats].apply(pd.to_numeric, errors='coerce').fillna(0.0).values
                try:
                    labels = obj.predict(X)
                    from sklearn.metrics import silhouette_score
                    report['silhouette'] = float(silhouette_score(X, labels))
                except Exception as e:
                    report['issues'].append('silhouette_failed:' + str(e))
        except Exception:
            pass

    return report


def validate_feature(obj, name: str):
    report = {'type': 'feature', 'status': 'OK', 'issues': []}
    if not isinstance(obj, (list, tuple)):
        report['status'] = 'BAD_FORMAT'
        report['issues'].append('not a list/tuple')
        return report
    if any(not isinstance(x, str) for x in obj):
        report['issues'].append('non-string feature names')
    if len(obj) != len(set(obj)):
        report['issues'].append('duplicate feature names')
    report['feature_count'] = len(obj)
    return report


def validate_metadata(obj, name: str, models_dir: Path):
    report = {'type': 'metadata', 'status': 'OK', 'issues': []}
    if not isinstance(obj, dict):
        report['status'] = 'BAD_FORMAT'
        report['issues'].append('not a dict')
        return report
    # required keys
    for k in ('model_name', 'target', 'feature_count'):
        if k not in obj:
            report['issues'].append('missing_key:' + k)
    # check referenced features exist
    if 'features' in obj:
        f = obj['features']
        if isinstance(f, (list, tuple)):
            report['feature_count'] = len(f)
        else:
            report['issues'].append('features_not_list')
    if 'feature_count' in obj and isinstance(obj['feature_count'], int):
        report['feature_count'] = int(obj['feature_count'])
    return report


def normalize_metadata_payload(obj, name: str):
    payload = dict(obj) if isinstance(obj, dict) else {}
    model_name = payload.get('model_name') or name.replace('.pkl', '').replace('.joblib', '')
    target = payload.get('target', '')
    features = payload.get('features') or payload.get('feature_names') or payload.get('base_features')
    feature_count = payload.get('feature_count')
    if not isinstance(feature_count, int) or feature_count <= 0:
        if isinstance(features, (list, tuple)):
            feature_count = len(features)
        else:
            feature_count = 0
    payload['model_name'] = model_name
    payload['target'] = target if target is not None else ''
    payload['feature_count'] = int(feature_count)
    return payload


def normalize_metadata_files(models_dir: Path):
    updated = []
    for p in sorted(models_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in ('.pkl', '.joblib'):
            continue
        if 'meta' not in p.name.lower() and 'metadata' not in p.name.lower():
            continue
        try:
            obj = joblib.load(p)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        payload = normalize_metadata_payload(obj, p.name)
        if payload != obj:
            joblib.dump(payload, p)
            updated.append(p.name)
    return updated


def validate_scaler(obj, name: str, models_dir: Path):
    report = {'type': 'scaler', 'status': 'OK', 'issues': []}
    if not hasattr(obj, 'transform'):
        report['status'] = 'BAD_FORMAT'
        report['issues'].append('no transform()')
        return report
    # test transform
    try:
        import numpy as _np
        arr = _np.zeros((2, getattr(obj, 'n_features_in_', 5)))
        obj.transform(arr)
        report['transform_ok'] = True
    except Exception as e:
        report['transform_ok'] = False
        report['issues'].append('transform_failed:' + str(e))
    return report


def find_feature_names(models_dir: Path, model_name: str):
    base = model_name.replace('.pkl', '')
    for p in models_dir.iterdir():
        if p.is_file() and ('feature' in p.name.lower()) and (base.split('_')[0] in p.name.lower()):
            return p
    # any feature file
    for p in models_dir.iterdir():
        if p.is_file() and ('feature' in p.name.lower()):
            return p
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models-dir', required=False, default='backend/ml_upgrade_models')
    parser.add_argument('--fix-metadata', action='store_true', help='Normalize metadata files in-place before validation')
    args = parser.parse_args()
    models_dir = Path(args.models_dir)
    if args.fix_metadata:
        updated = normalize_metadata_files(models_dir)
        if updated:
            print('Normalized metadata files:')
            for name in updated:
                print('-', name)
    out = {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'artifacts': []}

    for p in sorted(models_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in ('.pkl', '.joblib'):
            continue
        entry = {'file': p.name, 'path': str(p), 'type': None, 'status': None, 'details': {}}
        obj, err = safe_load(p)
        if err:
            entry['type'] = 'load_failed'
            entry['status'] = 'LOAD_FAILED'
            entry['details'] = {'error': err}
            out['artifacts'].append(entry)
            continue

        atype = detect_artifact_type(obj, p.name)
        entry['type'] = atype
        try:
            # Only validate actual predictive artifacts that implement .predict()
            if atype == 'regressor':
                entry['details'] = validate_regressor(obj, models_dir, p.name)
            elif atype == 'classifier':
                entry['details'] = validate_classifier(obj, models_dir, p.name)
            elif atype == 'clustering':
                entry['details'] = validate_clustering(obj, models_dir, p.name)
            elif atype == 'feature':
                entry['details'] = validate_feature(obj, p.name)
            elif atype == 'metadata':
                entry['details'] = validate_metadata(obj, p.name, models_dir)
            elif atype == 'scaler':
                entry['details'] = validate_scaler(obj, p.name, models_dir)
            elif atype == 'helper':
                entry['details'] = {'type': 'helper', 'status': 'SKIPPED', 'issues': ['helper_or_cache_artifact']}
            elif atype.endswith('_candidate'):
                # Filename suggested a model but object inspection did not confirm predictability.
                entry['details'] = {'type': atype, 'status': 'CANDIDATE_NOT_VALIDATED', 'issues': ['filename_suggests_model_but_object_not_predictive']}
            else:
                entry['details'] = {'type': 'unknown', 'repr': repr(obj)[:200]}
        except Exception as e:
            entry['status'] = 'VALIDATION_ERROR'
            entry['details'] = {'error': ''.join(traceback.format_exception_only(type(e), e)).strip()}
        if 'status' not in entry or entry['status'] is None:
            entry['status'] = entry['details'].get('status', 'OK')
        out['artifacts'].append(entry)

    # environment compatibility and backend ref checks
    out['compatibility'] = check_environment_compatibility()
    out['backend_references'] = scan_backend_references(models_dir)

    # write reports
    j = models_dir / 'validation_report.json'
    c = models_dir / 'validation_report.csv'
    j.write_text(json.dumps(out, indent=2))
    with open(c, 'w', newline='') as fh:
        fieldnames = ['file', 'type', 'status', 'issues']
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for a in out['artifacts']:
            issues = a.get('details', {}).get('issues') if a.get('details') else None
            writer.writerow({'file': a['file'], 'type': a['type'], 'status': a['status'], 'issues': ','.join(issues) if issues else ''})

    print('Wrote', j, 'and', c)


if __name__ == '__main__':
    main()
