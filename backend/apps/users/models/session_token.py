from datetime import datetime, timedelta

from mongoengine import DateTimeField, Document, ReferenceField, StringField

from .user import User


class SessionToken(Document):
    user = ReferenceField(User, required=True)
    token = StringField(required=True, unique=True)
    created_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(required=True)
    last_used_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'session_tokens',
        'indexes': [
            {'fields': ['token'], 'unique': True},
            'user',
            {'fields': ['expires_at'], 'expireAfterSeconds': 0},
            ('user', '-created_at'),
        ],
    }

    @classmethod
    def create_token(cls, user, token, ttl_seconds=7 * 24 * 3600):
        return cls(
            user=user,
            token=token,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        )