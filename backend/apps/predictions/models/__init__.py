from mongoengine import EmbeddedDocumentField
from .prediction_input import PredictionInput
from .prediction_result import PredictionResult, Location

__all__ = ['PredictionInput', 'PredictionResult', 'Location']
