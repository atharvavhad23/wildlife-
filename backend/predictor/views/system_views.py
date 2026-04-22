"""
System views: Authentication, home page, and photo proxy.
"""

import json
import secrets
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from urllib.parse import unquote
from urllib.request import urlopen
import warnings

warnings.filterwarnings('ignore')

from predictor.constants import OTP_TTL_SECONDS, SUCCESS_OTP_SENT, SUCCESS_VERIFIED
from predictor.constants import ERROR_EMAIL_INVALID, ERROR_SMTP_NOT_CONFIGURED, ERROR_INVALID_OTP, ERROR_OTP_EXPIRED


def _otp_key(email: str, purpose: str) -> str:
    """Generate cache key for OTP"""
    normalized = str(email).strip().lower()
    safe_purpose = str(purpose).strip().lower() or 'auth'
    return f"otp:{safe_purpose}:{normalized}"


def _otp_verified_key(email: str, purpose: str) -> str:
    """Generate cache key for OTP verification"""
    normalized = str(email).strip().lower()
    safe_purpose = str(purpose).strip().lower() or 'auth'
    return f"otp_verified:{safe_purpose}:{normalized}"


@csrf_exempt
@require_http_methods(["POST"])
def send_email_otp(request):
    """Send OTP code to email using configured project SMTP account."""
    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        payload = {}

    email = str(payload.get('email', '')).strip().lower()
    purpose = str(payload.get('purpose', 'auth')).strip().lower() or 'auth'

    if not email or '@' not in email:
        return JsonResponse({'error': ERROR_EMAIL_INVALID}, status=400)

    if not getattr(settings, 'EMAIL_HOST', '') or not getattr(settings, 'EMAIL_HOST_USER', ''):
        return JsonResponse(
            {'error': ERROR_SMTP_NOT_CONFIGURED},
            status=400,
        )

    otp = f"{secrets.randbelow(900000) + 100000}"
    cache.set(_otp_key(email, purpose), otp, timeout=OTP_TTL_SECONDS)
    cache.delete(_otp_verified_key(email, purpose))

    subject = f"Koyna Wildlife OTP for {purpose.title()}"
    message = (
        f"Your OTP is: {otp}\n\n"
        f"It will expire in {OTP_TTL_SECONDS // 60} minutes.\n"
        "If you did not request this, please ignore this email."
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception as exc:
        return JsonResponse({'error': f'Failed to send OTP email: {exc}'}, status=500)

    return JsonResponse({'status': 'success', 'message': SUCCESS_OTP_SENT})


@csrf_exempt
@require_http_methods(["POST"])
def verify_email_otp(request):
    """Verify OTP code sent to email."""
    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        payload = {}

    email = str(payload.get('email', '')).strip().lower()
    purpose = str(payload.get('purpose', 'auth')).strip().lower() or 'auth'
    code = str(payload.get('otp', '')).strip()

    if not email or '@' not in email:
        return JsonResponse({'error': ERROR_EMAIL_INVALID}, status=400)
    if not code:
        return JsonResponse({'error': 'OTP code is required.'}, status=400)

    stored = cache.get(_otp_key(email, purpose))
    if stored is None:
        return JsonResponse({'error': ERROR_OTP_EXPIRED}, status=400)

    if str(stored) != code:
        return JsonResponse({'error': ERROR_INVALID_OTP}, status=400)

    cache.set(_otp_verified_key(email, purpose), True, timeout=15 * 60)
    cache.delete(_otp_key(email, purpose))

    return JsonResponse({'status': 'success', 'verified': True, 'message': SUCCESS_VERIFIED})


@require_http_methods(["GET"])
def index(request):
    """Render home page"""
    return render(request, 'home.html')


@csrf_exempt
@require_http_methods(["GET"])
def photo_proxy(request):
    """
    Proxy external photo URLs.
    Usage: /photo-proxy/?url=<encoded_url>
    """
    try:
        encoded_url = request.GET.get('url', '')
        if not encoded_url:
            return HttpResponse('Missing URL parameter', status=400)

        photo_url = unquote(encoded_url)

        # Security: Only allow known domains
        allowed_domains = [
            'inaturalist.org',
            'commons.wikimedia.org',
            'upload.wikimedia.org',
            'github.com',
        ]

        if not any(domain in photo_url for domain in allowed_domains):
            return HttpResponse('URL domain not allowed', status=403)

        with urlopen(photo_url, timeout=5) as response:
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            return HttpResponse(response.read(), content_type=content_type)

    except Exception as e:
        return HttpResponse(f'Error fetching photo: {e}', status=500)
