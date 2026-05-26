from mongoengine import Document, EmbeddedDocument, ReferenceField, FloatField, StringField, DateTimeField, URLField, EmbeddedDocumentField, PointField
from datetime import datetime
from apps.species.models import Species


class Location(EmbeddedDocument):
    """
    Embedded document for geospatial coordinates using GeoJSON format.
    """
    lat = FloatField(required=True)
    lon = FloatField(required=True)

    def to_geojson(self):
        """Convert to GeoJSON Point format for geospatial indexing."""
        return {
            'type': 'Point',
            'coordinates': [self.lon, self.lat]
        }


class Observation(Document):
    """
    Observation model for tracking species sightings with geospatial data.
    """
    species = ReferenceField(Species, required=True)
    species_name = StringField()
    location = EmbeddedDocumentField(Location, required=True)
    geo_location = PointField()
    observed_at = DateTimeField(required=True, default=datetime.utcnow)
    source = StringField(required=True)
    image_url = URLField()
    image_source_url = URLField()
    image_local_path = StringField()
    image_cached_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'observations',
        'indexes': [
            'species',
            '$species_name',
            'species_name',
            'source',
            'observed_at',
            '-created_at',
            'geo_location',
            ('species', '-observed_at'),
            ('species', 'source'),
            ('species_name', '-observed_at'),
            ('source', '-observed_at'),
            ('species_name', 'observed_at'),
        ]
    }

    def save(self, *args, **kwargs):
        """Save observation and maintain geospatial index."""
        self.geo_location = [self.location.lon, self.location.lat]
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.species.name} at ({self.location.lat}, {self.location.lon})"
