from mongoengine import Document, EmbeddedDocument, StringField, EmbeddedDocumentField


class Taxonomy(EmbeddedDocument):
    """
    Embedded document for taxonomic classification.
    """
    kingdom = StringField(default="Animalia")
    phylum = StringField(required=True)
    class_name = StringField(required=True)
    order = StringField(required=True)
    family = StringField(required=True)
    genus = StringField()
    subspecies = StringField()


class Species(Document):
    """
    Species model with taxonomic and conservation information.
    """
    name = StringField(required=True, unique=True)
    scientific_name = StringField(required=True, unique=True)
    category = StringField(required=True, choices=['birds', 'animals', 'insects', 'plants'])
    taxonomy = EmbeddedDocumentField(Taxonomy, required=True)
    iucn_status = StringField(
        required=True,
        choices=['EX', 'EW', 'CR', 'EN', 'VU', 'NT', 'LC', 'DD', 'NE'],
        default='DD'
    )
    description = StringField()
    total_observations = StringField(default='0')

    meta = {
        'collection': 'species',
        'indexes': [
            '$name',
            {'fields': ['name'], 'unique': True},
            {'fields': ['scientific_name'], 'unique': True},
            'category',
            'iucn_status',
            ('category', 'iucn_status'),
            ('category', 'name'),
            ('category', 'scientific_name'),
            ('scientific_name', 'category'),
            ('iucn_status', 'category'),
        ]
    }

    def __str__(self):
        return f"{self.name} ({self.scientific_name})"
