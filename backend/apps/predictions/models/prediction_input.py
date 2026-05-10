from mongoengine import Document, ReferenceField, DictField, StringField, DateTimeField
from datetime import datetime
from apps.users.models import User


class PredictionInput(Document):
    """
    Model for storing user input data for predictions.
    """
    user = ReferenceField(User, required=True)
    category = StringField(required=True, choices=['birds', 'animals', 'insects', 'plants'])
    features = DictField(required=True)  # Variable feature set based on model
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'prediction_inputs',
        'indexes': [
            'user',
            'category',
            '-created_at',
            ('user', '-created_at'),
            ('category', '-created_at'),
            ('user', 'category', '-created_at'),
        ]
    }

    def __str__(self):
        return f"PredictionInput for {self.user.email} - {self.category}"
