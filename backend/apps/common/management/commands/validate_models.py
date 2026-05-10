from pathlib import Path
import logging
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

        ml_dir = base_dir / 'ml_models'
        log_file = options.get('log_file') or (ml_dir / 'validation.log')

        logger = logging.getLogger('validate_models')
        logger.setLevel(logging.DEBUG)
        # File handler
        fh = logging.FileHandler(str(log_file), encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        # Stream handler
        sh = logging.StreamHandler(self.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(formatter)
        # Avoid duplicate handlers
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
            # fallback local heuristics
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

        # Log discovered and classify
        results = []
        logger.info('Discovered %d artifacts', len(discovered))
        for p in sorted(discovered):
            name = p.name
            helper = _is_helper(name)
            score = _score(p)
            logger.info('Found: %s | helper=%s | score=%d', p, helper, score)
            results.append({'path': p, 'helper': helper, 'score': score, 'loaded': False, 'error': None})

        # Attempt safe joblib.load on each
        try:
            import joblib
        except Exception as exc:
            logger.error('joblib not available: %s', exc)
            return

        for r in results:
            p = r['path']
            try:
                logger.debug('Attempting load: %s', p)
                obj = joblib.load(str(p))
                r['loaded'] = True
                logger.info('SUCCESS loading %s: type=%s', p, type(obj).__name__)
                # free memory
                del obj
            except Exception as exc:
                r['loaded'] = False
                r['error'] = repr(exc)
                logger.exception('FAILED loading %s', p)

        # Pick best candidate (highest score, prefer loaded)
        loaded_candidates = [r for r in results if r['loaded'] and not r['helper']]
        if not loaded_candidates:
            # allow helper if no other
            loaded_candidates = [r for r in results if r['loaded']]

        if loaded_candidates:
            loaded_candidates.sort(key=lambda x: x['score'], reverse=True)
            best = loaded_candidates[0]
            logger.info('Best candidate: %s (score=%d)', best['path'], best['score'])
        else:
            logger.warning('No successfully loaded model artifacts found')
            best = None

        # Also consult prediction_service.find_model_path to see what runtime selection would be
        try:
            candidate = _find_model([])
            logger.info('prediction_service.find_model_path([]) returned: %s', candidate)
        except Exception:
            logger.exception('prediction_service.find_model_path failed')

        # Summary table
        logger.info('Validation summary:')
        for r in results:
            logger.info('%s | helper=%s | score=%d | loaded=%s | error=%s', r['path'], r['helper'], r['score'], r['loaded'], r['error'])

        # Final recommendation
        if best and best['loaded']:
            logger.info('/api/predict/ should be able to load a model at runtime and not return 503 (selected: %s)', best['path'])
        else:
            logger.warning('/api/predict/ will still return 503 until a loadable model artifact is placed under %s', ml_dir)
