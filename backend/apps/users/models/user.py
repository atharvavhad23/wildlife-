from mongoengine import Document, StringField, BooleanField, DateTimeField, EmailField
from datetime import datetime


class User(Document):
    """
    User model for authentication and profile management.
    """
    email = EmailField(required=True, unique=True)
    is_verified = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField(null=True)

    meta = {
        'collection': 'users',
        'indexes': [
            {'fields': ['email'], 'unique': True},
            'is_verified',
            '-created_at',
            'last_login',
            ('is_verified', '-created_at'),
        ]
    }

    def __str__(self):
        return self.email
