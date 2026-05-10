import logging
from functools import lru_cache

from pymongo.errors import DuplicateKeyError


logger = logging.getLogger(__name__)


def _ensure_indexes(document_classes):
    for document_class in document_classes:
        try:
            document_class.ensure_indexes()
        except DuplicateKeyError:
            logger.warning('Skipping index creation for %s because duplicate data already exists', document_class.__name__)
        except Exception:
            logger.exception('Failed to ensure indexes for %s', document_class.__name__)


@lru_cache(maxsize=1)
def bootstrap_backend() -> None:
    from apps.analytics.models import Alert, Cluster, DashboardCache, Media
    from apps.observations.models import Observation
    from apps.predictions.models import PredictionInput, PredictionResult
    from apps.species.models import Species
    from apps.users.models import OTP, SessionToken, User

    _ensure_indexes(
        [
            User,
            OTP,
            SessionToken,
            Species,
            Observation,
            PredictionInput,
            PredictionResult,
            Cluster,
            Alert,
            Media,
            DashboardCache,
        ]
    )