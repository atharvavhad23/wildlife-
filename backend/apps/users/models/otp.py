from mongoengine import Document, EmailField, StringField, DateTimeField
from datetime import datetime, timedelta


class OTP(Document):
    """
    One-Time Password model for email verification.
    Uses TTL index for automatic expiration.
    """
    email = EmailField(required=True)
    otp_code = StringField(required=True, unique=True)
    expires_at = DateTimeField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'otps',
        'indexes': [
            'email',
            {'fields': ['otp_code'], 'unique': True},
            {'fields': ['expires_at'], 'expireAfterSeconds': 3600},
            'created_at',
            ('email', '-created_at'),
        ]
    }

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @classmethod
    def create_otp(cls, email, otp_code, ttl_seconds=3600):
        """
        Create a new OTP record with automatic expiration.
        """
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        return cls(email=email, otp_code=otp_code, expires_at=expires_at)

    def __str__(self):
        return f"OTP for {self.email}"
