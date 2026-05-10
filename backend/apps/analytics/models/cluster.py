from mongoengine import Document, EmbeddedDocument, ReferenceField, FloatField, IntField, StringField, ListField, DateTimeField, EmbeddedDocumentField
from datetime import datetime
from apps.species.models import Species


class Centroid(EmbeddedDocument):
    """
    Embedded document for cluster centroid coordinates.
    """
    lat = FloatField(required=True)
    lon = FloatField(required=True)


class Cluster(Document):
    """
    Model for storing geographical clusters of species observations.
    Used for density analysis and spatial pattern recognition.
    """
    category = StringField(required=True, choices=['birds', 'animals', 'insects', 'plants'])
    cluster_id = StringField(required=True, unique=True)
    centroid = EmbeddedDocumentField(Centroid, required=True)
    species_count = IntField(default=0)
    dominant_species = ReferenceField(Species)
    species_list = ListField(ReferenceField(Species))
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'clusters',
        'indexes': [
            'category',
            'cluster_id',
            'species_count',
            'dominant_species',
            '-created_at',
            ('category', 'cluster_id'),
            ('category', '-created_at'),
            ('category', '-species_count'),
            ('dominant_species', '-created_at'),
        ]
    }

    def save(self, *args, **kwargs):
        """Update timestamp on save."""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Cluster {self.cluster_id} ({self.category})"
