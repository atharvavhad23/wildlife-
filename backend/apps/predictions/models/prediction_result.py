from mongoengine import Document, EmbeddedDocument, ReferenceField, FloatField, StringField, DateTimeField, DictField, EmbeddedDocumentField
from datetime import datetime
from apps.users.models import User
from apps.species.models import Species
from .prediction_input import PredictionInput


class Location(EmbeddedDocument):
    """
    Embedded location for prediction results.
    """
    lat = FloatField(required=True)
    lon = FloatField(required=True)


class PredictionResult(Document):
    """
    Model for storing ML prediction results with metadata and performance tracking.
    """
    user = ReferenceField(User, required=True)
    input = ReferenceField(PredictionInput)
    species = ReferenceField(Species)
    predicted_density = FloatField(required=True)
    confidence_score = FloatField(required=True, min_value=0, max_value=1)
    model_version = StringField(required=True)
    input_snapshot = DictField(required=True)  # Store input features at prediction time
    location = EmbeddedDocumentField(Location)
    status = StringField(
        required=True,
        choices=['success', 'failed', 'pending'],
        default='pending'
    )
    error_message = StringField()  # Store error details if status is 'failed'
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'prediction_results',
        'indexes': [
            'user',
            'input',
            'species',
            'model_version',
            'status',
            'predicted_density',
            'confidence_score',
            'updated_at',
            '-created_at',
            ('user', '-created_at'),
            ('species', '-created_at'),
            ('model_version', 'status'),
            ('status', '-created_at'),
            ('species', 'status', '-created_at'),
            ('user', 'species', '-created_at'),
        ]
    }

    def save(self, *args, **kwargs):
        """Update timestamp on save."""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        species_name = self.species.name if self.species else 'Unknown'
        return f"Prediction: {species_name} (confidence: {self.confidence_score:.2f})"
