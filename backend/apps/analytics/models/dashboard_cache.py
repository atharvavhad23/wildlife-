from mongoengine import Document, StringField, DictField, DateTimeField
from datetime import datetime, timedelta


class DashboardCache(Document):
    """
    Model for caching dashboard statistics and aggregated data.
    Optimizes read performance for analytics queries.
    """
    category = StringField(required=True, choices=['birds', 'animals', 'insects', 'plants'])
    stats = DictField(required=True)  # Stores aggregated statistics
    last_updated = DateTimeField(default=datetime.utcnow)
    cache_expiry = DateTimeField()  # Manual expiry timestamp

    meta = {
        'collection': 'dashboard_cache',
        'indexes': [
            'category',
            '-last_updated',
            'cache_expiry',
            ('category', '-last_updated'),
        ]
    }

    def save(self, *args, **kwargs):
        """Update cache timestamp on save."""
        self.last_updated = datetime.utcnow()
        return super().save(*args, **kwargs)

    def is_stale(self, max_age_seconds=3600):
        """Check if cache is stale."""
        return datetime.utcnow() - self.last_updated > timedelta(seconds=max_age_seconds)

    def __str__(self):
        return f"Dashboard Cache for {self.category}"
