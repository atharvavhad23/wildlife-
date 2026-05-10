from mongoengine import Document, ReferenceField, StringField, DateTimeField
from datetime import datetime
from apps.species.models import Species


class Media(Document):
    """
    Model for storing media references (images, videos) associated with species.
    """
    species = ReferenceField(Species, required=True)
    image_url = StringField(required=True)
    source = StringField(required=True)
    media_type = StringField(choices=['image', 'video'], default='image')
    fetched_at = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'media',
        'indexes': [
            'species',
            'source',
            'media_type',
            '-fetched_at',
            '-created_at',
            ('species', '-fetched_at'),
            ('source', '-created_at'),
            ('species', 'media_type'),
            ('source', 'media_type'),
        ]
    }

    def __str__(self):
        return f"Media for {self.species.name} from {self.source}"
