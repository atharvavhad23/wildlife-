from mongoengine import Document, ReferenceField, StringField, DateTimeField
from datetime import datetime
from apps.species.models import Species


class Alert(Document):
    """
    Model for conservation and population alerts.
    Tracks critical observations and warnings.
    """
    species = ReferenceField(Species, required=True)
    alert_type = StringField(
        required=True,
        choices=['population_decline', 'endangered_sighting', 'range_expansion', 'unusual_activity'],
        indexed=True
    )
    message = StringField(required=True)
    severity = StringField(
        required=True,
        choices=['low', 'medium', 'high', 'critical'],
        default='medium'
    )
    is_resolved = StringField(default='False')
    created_at = DateTimeField(default=datetime.utcnow)
    resolved_at = DateTimeField()

    meta = {
        'collection': 'alerts',
        'indexes': [
            'species',
            'alert_type',
            'severity',
            'is_resolved',
            '-created_at',
            'resolved_at',
            ('alert_type', '-created_at'),
            ('species', 'alert_type'),
            ('severity', '-created_at'),
            ('species', '-created_at'),
            ('is_resolved', '-created_at'),
            ('alert_type', 'severity'),
        ]
    }

    def __str__(self):
        return f"Alert: {self.alert_type} for {self.species.name}"
