"""Validate compatibility of artifacts in backend/ml_models for binding into prediction service.

Usage: python validation.py
Writes JSON and CSV summary to backend/ml_models/compatibility_report.*
"""
from pathlib import Path
import json
import csv
import time
import traceback

BASE = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE / 'ml_models'

def main():
    out = {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'results': []}
    if not MODEL_DIR.exists():
        print('No ml_models directory found at', MODEL_DIR)
        return 1

    # import prediction service from project
    try:
        from backend.apps.common import prediction_service as ps
    except Exception:
        # try relative import fallback
        import sys
        sys.path.append(str(Path(__file__).resolve().parents[2]))
        from backend.apps.common import prediction_service as ps

    for p in sorted(MODEL_DIR.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in ('.pkl', '.joblib'):
            continue

        entry = {'file': p.name, 'path': str(p), 'status': 'UNKNOWN', 'error': None, 'has_predict': False, 'has_proba': False, 'n_features_in': None}
        try:
            # skip helper/meta files but still try to load them safely
            is_helper = ps._is_helper_file(p.name)
            try:
                model = ps.load_model(p)
            except Exception as e:
                entry['status'] = 'LOAD_FAILED'
                entry['error'] = str(e)
                out['results'].append(entry)
                print('LOAD_FAILED', p.name, e)
                continue

            entry['status'] = 'LOADED'
            entry['has_predict'] = hasattr(model, 'predict')
            entry['has_proba'] = hasattr(model, 'predict_proba')
            entry['n_features_in'] = getattr(model, 'n_features_in_', None)

            # build a sample input for prediction
            import numpy as np
            n = entry['n_features_in'] or 5
            X = np.zeros((1, int(n)))

            # attempt a prediction call using prediction_service helper
            try:
                preds, conf = ps.predict_density(model, X)
                entry['status'] = 'PREDICT_OK'
                entry['sample_prediction'] = None
                try:
                    entry['sample_prediction'] = float(preds[0]) if hasattr(preds, '__len__') else float(preds)
                except Exception:
                    entry['sample_prediction'] = str(preds)
                if conf is not None:
                    try:
                        entry['sample_confidence'] = float(conf[0]) if hasattr(conf, '__len__') else float(conf)
                    except Exception:
                        entry['sample_confidence'] = str(conf)
            except Exception as e:
                entry['status'] = 'PREDICT_FAILED'
                entry['error'] = ''.join(traceback.format_exception_only(type(e), e)).strip()
                print('PREDICT_FAILED', p.name, entry['error'])

        except Exception as e:
            entry['status'] = 'ERROR'
            entry['error'] = ''.join(traceback.format_exception_only(type(e), e)).strip()
        out['results'].append(entry)

    # write outputs
    jpath = MODEL_DIR / 'compatibility_report.json'
    cpath = MODEL_DIR / 'compatibility_report.csv'
    jpath.write_text(json.dumps(out, indent=2))

    # CSV summary
    with open(cpath, 'w', newline='') as fh:
        fieldnames = ['file', 'status', 'has_predict', 'has_proba', 'n_features_in', 'sample_prediction', 'sample_confidence', 'error']
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in out['results']:
            writer.writerow({k: r.get(k) for k in fieldnames})

    print('Wrote', jpath, 'and', cpath)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
