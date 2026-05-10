"""Validate model artifacts in an arbitrary models directory.

Usage: python validate_dir.py --models-dir <path>
Writes <models-dir>/compatibility_report.json and .csv
"""
from pathlib import Path
import argparse
import json
import csv
import time
import traceback

def validate_dir(models_dir: Path):
    out = {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'results': []}
    if not models_dir.exists() or not models_dir.is_dir():
        raise SystemExit(f'models dir not found: {models_dir}')

    # lazy import prediction_service
    try:
        from backend.apps.common import prediction_service as ps
    except Exception:
        import sys
        sys.path.append(str(Path(__file__).resolve().parents[2]))
        from backend.apps.common import prediction_service as ps

    for p in sorted(models_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in ('.pkl', '.joblib'):
            continue

        entry = {'file': p.name, 'path': str(p), 'status': 'UNKNOWN', 'error': None, 'has_predict': False, 'has_proba': False, 'n_features_in': None}
        try:
            try:
                model = ps.load_model(p)
            except Exception as e:
                entry['status'] = 'LOAD_FAILED'
                entry['error'] = str(e)
                out['results'].append(entry)
                continue

            entry['status'] = 'LOADED'
            entry['has_predict'] = hasattr(model, 'predict')
            entry['has_proba'] = hasattr(model, 'predict_proba')
            entry['n_features_in'] = getattr(model, 'n_features_in_', None)

            # attempt sample predict
            import numpy as np
            n = entry['n_features_in'] or 5
            X = np.zeros((1, int(n)))
            try:
                preds, conf = ps.predict_density(model, X)
                entry['status'] = 'PREDICT_OK'
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

        except Exception as e:
            entry['status'] = 'ERROR'
            entry['error'] = ''.join(traceback.format_exception_only(type(e), e)).strip()
        out['results'].append(entry)

    jpath = models_dir / 'compatibility_report.json'
    cpath = models_dir / 'compatibility_report.csv'
    jpath.write_text(json.dumps(out, indent=2))
    with open(cpath, 'w', newline='') as fh:
        fieldnames = ['file', 'status', 'has_predict', 'has_proba', 'n_features_in', 'sample_prediction', 'sample_confidence', 'error']
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
