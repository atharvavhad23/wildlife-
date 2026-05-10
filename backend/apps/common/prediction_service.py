"""
Prediction service with lazy-loaded ML models and caching.
Models are only loaded on first prediction request, not at startup.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Artifact cache (loaded on first use)
_artifact_cache = {}
_cache_lock = None


def _get_cache_lock():
    """Get or create thread-safe cache lock."""
    global _cache_lock
    if _cache_lock is None:
        import threading
        _cache_lock = threading.Lock()
    return _cache_lock


def load_artifact(artifact_path):
    """
    Load and cache a serialized artifact from disk.
    Thread-safe. Returns cached model on subsequent calls.
    """
    path = Path(artifact_path)
    path_str = str(path)
    
    # Fast path: already cached
    if path_str in _artifact_cache:
        return _artifact_cache[path_str]
    
    # Slow path: load and cache
    with _get_cache_lock():
        # Check again in case another thread loaded it
        if path_str in _artifact_cache:
            return _artifact_cache[path_str]
        
        try:
            # Verify file exists before attempting load
            if not path.exists():
                print(f"Missing model: {path}")
                raise FileNotFoundError(f"Model file not found: {path}")

            import joblib
            artifact = joblib.load(path)
            _artifact_cache[path_str] = artifact
            logger.info('Loaded artifact from %s', path)
            print(f"Loaded artifact: {path}")
            return artifact
        except Exception as e:
            logger.exception('Failed to load artifact from %s', path)
            # Re-raise after logging for callers to handle
            raise


def load_model(model_path):
    """Backward-compatible alias for loading serialized models."""
    return load_artifact(model_path)


def _is_helper_file(name: str) -> bool:
    """Return True if filename looks like metadata/scaler/feature file to ignore as main model."""
    lower = name.lower()
    helpers = ('scaler', 'scale', 'standardscaler', 'minmax', 'encoder', 'label', 'labels', 'meta', 'metadata', 'feature', 'features', 'importance', 'config', 'params', 'occurrence_features', 'occurrence_metadata', 'compatibility', 'conversion', 'legacy', 'thumbnail_cache')
    for h in helpers:
        if h in lower:
            return True
    return False


def _score_model_path(path: Path) -> int:
    """Score candidate model paths so we can pick the most-likely main model.

    Higher score = more likely main model. Heuristics:
    - filenames containing 'model','predict','density' get higher score
    - filenames containing dataset names get good score
    - helper files (scaler/metadata/feature) get negative influence
    """
    name = path.name.lower()
    score = 0
    if 'model' in name or 'predict' in name or 'density' in name:
        score += 50
    for token, pts in (('birds', 20), ('insects', 20), ('animals', 20), ('plants', 10), ('universal', 5)):
        if token in name:
            score += pts
    # deprioritize obvious helper files
    if _is_helper_file(name):
        score -= 100
    # prefer .pkl slightly over .joblib for legacy
    if path.suffix == '.pkl':
        score += 5
    return score


def find_model_path(candidates):
    """Find best existing model from list of candidate paths or by scanning ml_models.

    Returns Path or None.
    """
    # First, honor explicit candidates (first-existing wins)
    for candidate in candidates:
        try:
            p = Path(candidate)
        except Exception:
            p = Path(str(candidate))
        if p.exists():
            logger.debug('Found explicit candidate model: %s', p)
            return p

    # If none of the explicit candidates exists, attempt to scan BASE_DIR/ml_models
    try:
        from django.conf import settings
        base_dir = Path(getattr(settings, 'BASE_DIR', Path(__file__).resolve().parents[2]))
    except Exception:
        # Fallback to repo root (two parents up from this file)
        base_dir = Path(__file__).resolve().parents[2]

    ml_dir = base_dir / 'ml_models'
    # Debug verification for model dir resolution
    try:
        print("MODEL_DIR =", ml_dir)
        print("EXISTS =", ml_dir.exists())
    except Exception:
        pass
    discovered = []
    if ml_dir.exists() and ml_dir.is_dir():
        logger.debug('Scanning ml_models directory for artifacts: %s', ml_dir)
        for ext in ('*.pkl', '*.joblib'):
            for p in ml_dir.rglob(ext):
                discovered.append(Path(p))

    # log discovered files
    if discovered:
        logger.info('Discovered %d model/artifact files under %s', len(discovered), ml_dir)
        for p in discovered:
            logger.debug('Discovered artifact: %s', p)
    else:
        logger.debug('No artifacts discovered under ml_models (%s)', ml_dir)

    # Filter out helper files, score remaining candidates
    scored = []
    for p in discovered:
        score = _score_model_path(p)
        scored.append((score, p))

    if not scored:
        return None

    # pick highest score; if all negative due to helper detection, still pick highest
    scored.sort(key=lambda x: x[0], reverse=True)
    selected_score, selected_path = scored[0]
    logger.info('Selected model artifact: %s (score=%d)', selected_path, selected_score)
    return selected_path


def predict_density(model, features_list):
    """
    Make predictions using loaded model.
    
    Args:
        model: Loaded model object (sklearn, xgboost, etc.)
        features_list: List of feature arrays [[lat, lon, temp, humidity], ...]
    
    Returns:
        predictions: Array of predicted values
        confidence: Array of confidence scores or None
    """
    try:
        predictions = model.predict(features_list)
        confidence = None
        
        # Try to extract confidence scores
        if hasattr(model, 'predict_proba'):
            try:
                probabilities = model.predict_proba(features_list)
                confidence = [float(max(p)) for p in probabilities]
            except Exception:
                pass
        
        if confidence is None and hasattr(model, 'decision_function'):
            try:
                decision = model.decision_function(features_list)
                if hasattr(decision, '__len__'):
                    confidence = [float(d) for d in decision]
                else:
                    confidence = [float(decision)]
            except Exception:
                pass
        
        return predictions, confidence
    except Exception as e:
        logger.exception('Prediction failed')
        raise


def normalize_prediction_output(prediction_value, confidence_score=None):
    """Normalize prediction output to safe JSON format."""
    try:
        prediction = float(prediction_value)
        if prediction_value is not None and hasattr(prediction_value, 'item'):
            prediction = float(prediction_value.item())
    except (TypeError, ValueError):
        prediction = 0.0
    
    if confidence_score is not None:
        try:
            confidence = float(confidence_score)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = None
    else:
        confidence = None
    
    return prediction, confidence
