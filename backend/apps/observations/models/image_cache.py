from datetime import datetime

from mongoengine import DateTimeField, Document, IntField, StringField, URLField


class ObservationImageCache(Document):
    cache_key = StringField(required=True, unique=True)
    source_url = URLField()
    occurrence_url = URLField()
    species_name = StringField()
    category = StringField()
    local_path = StringField(required=True)
    local_url = StringField(required=True)
    content_type = StringField(default='image/jpeg')
    byte_size = IntField(default=0)
    source = StringField(default='inaturalist')
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    last_accessed_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'observation_image_cache',
        'indexes': [
            {'fields': ['cache_key'], 'unique': True},
            'source_url',
            'occurrence_url',
            'species_name',
            'category',
            '-updated_at',
        ],
    }