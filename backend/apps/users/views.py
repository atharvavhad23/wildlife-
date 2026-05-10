import json
import secrets
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.users.auth import generate_session_token
from apps.users.models import OTP, User


OTP_TTL_SECONDS = 10 * 60


def _normalize_text(value):
    if value is None:
        return ''
    text = str(value).strip().lower()
    return '' if text in {'', 'nan', 'none', 'null'} else text


def _read_payload(request):
    try:
        return json.loads(request.body or '{}')
    except Exception:
        return {}


@csrf_exempt
@require_http_methods(["POST"])
def send_otp_view(request):
    try:
        payload = _read_payload(request)
        email = _normalize_text(payload.get('email'))
        if not email or '@' not in email:
            return JsonResponse({'error': 'Valid email is required.'}, status=400)

        otp_code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = datetime.utcnow() + timedelta(seconds=OTP_TTL_SECONDS)

        user = User.objects(email=email).first()
        if user is None:
            user = User(email=email)
            user.save()

        OTP.objects(email=email).delete()
        OTP(email=email, otp_code=otp_code, expires_at=expires_at).save()

        return JsonResponse({'status': 'success', 'message': 'OTP sent.'}, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to send OTP.'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp_view(request):
    try:
        payload = _read_payload(request)
        email = _normalize_text(payload.get('email'))
        otp_code = _normalize_text(payload.get('otp'))

        if not email or '@' not in email:
            return JsonResponse({'error': 'Valid email is required.'}, status=400)
        if not otp_code:
            return JsonResponse({'error': 'OTP code is required.'}, status=400)

        otp_record = OTP.objects(email=email, otp_code=otp_code).order_by('-created_at').first()
        if otp_record is None or otp_record.is_expired():
            return JsonResponse({'error': 'Invalid or expired OTP.'}, status=400)

        user = User.objects(email=email).first()
        if user is None:
            user = User(email=email)
        user.is_verified = True
        user.last_login = datetime.utcnow()
        user.save()

        otp_record.delete()
        session = generate_session_token(user)

        return JsonResponse(
            {
                'status': 'success',
                'verified': True,
                'user_id': str(user.id),
                'token': session.token,
            },
            status=200,
        )
    except Exception:
        return JsonResponse({'error': 'Failed to verify OTP.'}, status=500)