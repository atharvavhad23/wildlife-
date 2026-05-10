from pathlib import Path
import logging
import subprocess
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Recursively discover and validate ML artifacts under BASE_DIR/ml_models'

    def add_arguments(self, parser):
        parser.add_argument('--log-file', dest='log_file', help='Optional log file path')

    def handle(self, *args, **options):
        # Configure logger
        try:
            from django.conf import settings
            base_dir = Path(getattr(settings, 'BASE_DIR', Path(__file__).resolve().parents[3]))
        except Exception:
            base_dir = Path(__file__).resolve().parents[3]

        # Try to locate ml_models in reasonable parent locations
        ml_dir = None
        candidates = [base_dir] + list(base_dir.parents[:4])
        for cand in candidates:
            cand_ml = cand / 'ml_models'
            if cand_ml.exists() and cand_ml.is_dir():
                ml_dir = cand_ml
                break
        if ml_dir is None:
            ml_dir = base_dir / 'ml_models'

        log_file = options.get('log_file') or (ml_dir / 'validation.log')

        logger = logging.getLogger('validate_models')
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(str(log_file), encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        sh = logging.StreamHandler(self.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(formatter)
        if not logger.handlers:
            logger.addHandler(fh)
            logger.addHandler(sh)

        logger.info('BASE_DIR resolved to: %s', base_dir)
        logger.info('Scanning ml_models directory: %s', ml_dir)

        discovered = []
        if ml_dir.exists() and ml_dir.is_dir():
            for ext in ('*.pkl', '*.joblib'):
                for p in ml_dir.rglob(ext):
                    discovered.append(Path(p))

        if not discovered:
            logger.warning('No .pkl or .joblib artifacts found under %s', ml_dir)
            return

        # Import heuristics from prediction_service if available
        try:
            from apps.common import prediction_service as ps
            _is_helper = ps._is_helper_file
            _score = ps._score_model_path
            _find_model = ps.find_model_path
        except Exception:
            def _is_helper(name: str) -> bool:
                lower = name.lower()
                helpers = ('scaler', 'scale', 'standardscaler', 'minmax', 'encoder', 'label', 'labels', 'meta', 'metadata', 'feature', 'features', 'importance', 'config', 'params')
                return any(h in lower for h in helpers)

            def _score(path: Path) -> int:
                name = path.name.lower()
                score = 0
                if 'model' in name or 'predict' in name or 'density' in name:
                    score += 50
                for token, pts in (('birds', 20), ('insects', 20), ('animals', 20), ('plants', 10), ('universal', 5)):
                    if token in name:
                        score += pts
                if _is_helper(name):
                    score -= 100
                if path.suffix == '.pkl':
                    score += 5
                return score

            def _find_model(candidates):
                return None

        results = []
        logger.info('Discovered %d artifacts', len(discovered))
        for p in sorted(discovered):
            name = p.name
            helper = _is_helper(name)
            score = _score(p)
            logger.info('Found: %s | helper=%s | score=%d', p, helper, score)
            results.append({'path': p, 'helper': helper, 'score': score, 'loaded': False, 'error': None})

        for r in results:
            p = r['path']
            try:
                logger.debug('Attempting load: %s', p)
                if not p.exists():
                    raise FileNotFoundError(str(p))

                loader_code = (
                    "from pathlib import Path; import joblib, pickle, sys, json\n"
                    f"path = Path(r'''{str(p)}''')\n"
                    "def _sample_predict(obj):\n"
                    "    if not hasattr(obj, 'predict'):\n"
                    "        return ('NO_PREDICT', None)\n"
                    "    n = getattr(obj, 'n_features_in_', None)\n"
                    "    if n is None and hasattr(obj, 'feature_names_in_'):\n"
                    "        n = len(getattr(obj, 'feature_names_in_', []))\n"
                    "    if not n:\n"
                    "        return ('NO_SHAPE', None)\n"
                    "    import numpy as np\n"
                    "    sample = np.zeros((1, int(n)), dtype=float)\n"
                    "    try:\n"
                    "        out = obj.predict(sample)\n"
                    "        return ('OK', out[0] if hasattr(out, '__len__') else out)\n"
                    "    except Exception as ex:\n"
                    "        return ('PREDICT_FAIL', repr(ex))\n"
                    "try:\n"
                    "    obj = joblib.load(path)\n"
                    "    loader = 'joblib'\n"
                    "except Exception as e1:\n"
                    "    try:\n"
                    "        with open(path, 'rb') as fh:\n"
                    "            obj = pickle.load(fh, encoding='latin1')\n"
                    "        loader = 'pickle'\n"
                    "    except Exception as e2:\n"
                    "        print('ERROR|' + repr(e1) + '|' + repr(e2))\n"
                    "        sys.exit(2)\n"
                    "sample_status, sample_value = _sample_predict(obj)\n"
                    "print('OK|' + loader + '|' + type(obj).__name__ + '|' + sample_status + '|' + str(sample_value))\n"
                )
                proc = subprocess.run([sys.executable, '-c', loader_code], capture_output=True, text=True, timeout=45)
                stdout = (proc.stdout or '').strip()
                stderr = (proc.stderr or '').strip()
                if proc.returncode == 0 and stdout.startswith('OK|'):
                    parts = stdout.split('|', 4)
                    loader = parts[1] if len(parts) > 1 else 'unknown'
                    obj_type = parts[2] if len(parts) > 2 else 'unknown'
                    sample_status = parts[3] if len(parts) > 3 else 'unknown'
                    sample_value = parts[4] if len(parts) > 4 else ''
                    r['loaded'] = True
                    r['error'] = None
                    logger.info('SUCCESS loading %s via %s: type=%s', p, loader, obj_type)
                    if sample_status == 'OK':
                        logger.info('SAMPLE PREDICTION %s => %s', p, sample_value)
                    else:
                        logger.info('SAMPLE PREDICTION SKIPPED %s => %s', p, sample_status)
                else:
                    r['loaded'] = False
                    r['error'] = stdout or stderr or f'returncode={proc.returncode}'
                    logger.warning('FAILED loading %s: %s', p, r['error'])
            except subprocess.TimeoutExpired as exc:
                r['loaded'] = False
                r['error'] = f'Timeout: {exc}'
                logger.exception('Timeout loading %s', p)
            except Exception as exc:
                r['loaded'] = False
                r['error'] = repr(exc)
                logger.exception('FAILED loading %s', p)

        loaded_candidates = [r for r in results if r['loaded'] and not r['helper']]
        if not loaded_candidates:
            loaded_candidates = [r for r in results if r['loaded']]

        if loaded_candidates:
            loaded_candidates.sort(key=lambda x: x['score'], reverse=True)
            best = loaded_candidates[0]
            logger.info('Best candidate: %s (score=%d)', best['path'], best['score'])
        else:
            logger.warning('No successfully loaded model artifacts found')
            best = None

        try:
            candidate = _find_model([])
            logger.info('prediction_service.find_model_path([]) returned: %s', candidate)
        except Exception:
            logger.exception('prediction_service.find_model_path failed')

        logger.info('Validation summary:')
        for r in results:
            logger.info('%s | helper=%s | score=%d | loaded=%s | error=%s', r['path'], r['helper'], r['score'], r['loaded'], r['error'])

        if best and best['loaded']:
            logger.info('/api/predict/ should be able to load a model at runtime and not return 503 (selected: %s)', best['path'])
        else:
            logger.warning('/api/predict/ will still return 503 until a loadable model artifact is placed under %s', ml_dir)
