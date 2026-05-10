from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.common.prediction_service import load_model, find_model_path, predict_density, normalize_prediction_output
from apps.predictions.models import PredictionResult
from apps.users.auth import get_user_from_token
from apps.users.models import User


def _normalize_text(value):
    if value is None:
        return ''
    text = str(value).strip()
    return '' if text.lower() in {'', 'nan', 'none', 'null'} else text


def _float_field(payload, key):
    try:
        return float(payload.get(key))
    except (TypeError, ValueError):
        raise ValueError(f'{key} must be a number.')


def _bool_query_param(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _read_payload(request):
    payload = request.POST.dict() if request.POST else {}
    if payload:
        return payload
    import json

    try:
        return json.loads(request.body or '{}')
    except Exception:
        return {}


def _candidate_model_paths():
    configured = _normalize_text(getattr(settings, 'PREDICTION_MODEL_PATH', ''))
    if configured:
        yield Path(configured)

    base_dir = Path(settings.BASE_DIR)
    candidates = [
        base_dir / 'models' / 'prediction_model.pkl',
        base_dir / 'ml_logic' / 'wildlife_model.pkl',
        base_dir / 'wildlife_model.pkl',
    ]
    for candidate in candidates:
        yield candidate

    # Also consider a dedicated ml_models directory and any artifacts inside it.
    ml_dir = base_dir / 'ml_models'
    if ml_dir.exists() and ml_dir.is_dir():
        # yield any top-level expected names first
        for name in ('animals_model.pkl', 'birds_model.pkl', 'insects_model.pkl', 'density_model.pkl'):
            path = ml_dir / name
            if path.exists():
                yield path

        # then yield any .pkl or .joblib files found under ml_models (recursive)
        for p in sorted(ml_dir.rglob('*.pkl')):
            yield p
        for p in sorted(ml_dir.rglob('*.joblib')):
            yield p


@csrf_exempt
@require_http_methods(["POST"])
def predict_view(request):
    try:
        payload = _read_payload(request)

        missing_fields = [field for field in ('lat', 'lon', 'temperature', 'humidity') if field not in payload or str(payload.get(field)).strip() == '']
        if missing_fields:
            return JsonResponse({'error': 'Missing required fields.', 'missing_fields': missing_fields}, status=400)

        lat = _float_field(payload, 'lat')
        lon = _float_field(payload, 'lon')
        temperature = _float_field(payload, 'temperature')
        humidity = _float_field(payload, 'humidity')
        save_prediction = _bool_query_param(request.GET.get('save', 'false'))
        user = get_user_from_token(request)

        # Lazy-load model on first use
        model_path = find_model_path(_candidate_model_paths())
        if model_path is None:
            return JsonResponse({'error': 'No prediction model available.'}, status=503)

        model = load_model(model_path)
        features = [[lat, lon, temperature, humidity]]

        predictions, confidences = predict_density(model, features)
        prediction_value = predictions[0].item() if hasattr(predictions[0], 'item') else predictions[0]
        confidence_score = confidences[0] if confidences else None

        prediction_normalized, confidence_normalized = normalize_prediction_output(prediction_value, confidence_score)

        response = {
            'predicted_density': prediction_normalized,
            'confidence_score': confidence_normalized,
        }

        if save_prediction:
            if user is None:
                return JsonResponse({'error': 'Valid token is required to save prediction.'}, status=401)

            try:
                prediction_record = PredictionResult(
                    user=user,
                    predicted_density=prediction_normalized,
                    confidence_score=confidence_normalized if confidence_normalized is not None else 0.0,
                    model_version=_normalize_text(getattr(settings, 'PREDICTION_MODEL_VERSION', 'default')) or 'default',
                    input_snapshot={
                        'lat': lat,
                        'lon': lon,
                        'temperature': temperature,
                        'humidity': humidity,
                    },
                    status='success',
                )
                prediction_record.save()
                response['saved'] = True
                response['prediction_id'] = str(prediction_record.id)
            except Exception:
                response['saved'] = False

        return JsonResponse(response, status=200)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except FileNotFoundError as exc:
        return JsonResponse({'error': str(exc)}, status=503)
    except Exception:
        return JsonResponse({'error': 'Prediction failed.'}, status=500)


@require_http_methods(["GET"])
def prediction_history_view(request):
    try:
        user = get_user_from_token(request)
        if user is None:
            return JsonResponse({'error': 'Valid token is required.'}, status=401)

        try:
            offset = max(int(request.GET.get('offset', 0) or 0), 0)
        except (TypeError, ValueError):
            offset = 0

        try:
            limit = int(request.GET.get('limit', 20) or 20)
        except (TypeError, ValueError):
            limit = 20
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100

        queryset = PredictionResult.objects(user=user).only(
            'predicted_density', 'confidence_score', 'input_snapshot', 'model_version', 'created_at', 'status'
        ).order_by('-created_at')
        total_count = queryset.count()

        results = []
        for prediction in queryset.skip(offset).limit(limit):
            results.append(
                {
                    'id': str(prediction.id),
                    'predicted_density': prediction.predicted_density,
                    'confidence_score': prediction.confidence_score,
                    'input_snapshot': prediction.input_snapshot,
                    'model_version': prediction.model_version,
                    'created_at': prediction.created_at.isoformat() if prediction.created_at else None,
                    'status': prediction.status,
                }
            )

        return JsonResponse({'count': total_count, 'results': results, 'offset': offset, 'limit': limit}, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch prediction history.'}, status=500)