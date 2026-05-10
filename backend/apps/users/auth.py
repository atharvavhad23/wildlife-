import secrets
from datetime import datetime

from apps.users.models import SessionToken, User


def generate_session_token(user, ttl_seconds=7 * 24 * 3600):
    token = secrets.token_urlsafe(32)
    SessionToken.objects(user=user).delete()
    session = SessionToken.create_token(user=user, token=token, ttl_seconds=ttl_seconds)
    session.save()
    return session


def parse_token_from_request(request):
    header = request.META.get('HTTP_AUTHORIZATION', '') or request.META.get('HTTP_X_SESSION_TOKEN', '')
    header = str(header).strip()
    if not header:
        return ''
    if header.lower().startswith('token '):
        return header.split(' ', 1)[1].strip()
    return header


def get_user_from_token(request):
    token = parse_token_from_request(request)
    if not token:
        return None

    session = SessionToken.objects(token=token).first()
    if session is None:
        return None

    if session.expires_at and session.expires_at <= datetime.utcnow():
        session.delete()
        return None

    session.last_used_at = datetime.utcnow()
    session.save()
    return session.user