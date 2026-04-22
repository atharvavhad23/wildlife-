"""
Model loading and caching service.
Handles loading ML models from disk with caching.
"""

import joblib
from pathlib import Path
from typing import Dict, Optional, Tuple
import warnings

import wildlife_config
from predictor.constants.model_features import FEATURE_SETS, OCCURRENCE_FEATURE_SETS

warnings.filterwarnings('ignore')


class ModelLoader:
    """Centralized model loading and caching"""
    
    # In-memory caches
    _model_cache: Dict[str, object] = {}
    _scaler_cache: Dict[str, object] = {}
    _feature_cache: Dict[str, list] = {}
    _metadata_cache: Dict[str, Dict] = {}
    _occurrence_classifier_cache: Dict[str, object] = {}
    _occurrence_features_cache: Dict[str, list] = {}
    _occurrence_metadata_cache: Dict[str, Dict] = {}
    
    # Special for plants
    _kmeans_cache: Dict[str, object] = {}
    _kmeans_scaler_cache: Dict[str, object] = {}
    _kmeans_meta_cache: Dict[str, Dict] = {}
    
    @staticmethod
    def load_model(category: str) -> Optional[object]:
        """
        Load regression model for category.
        
        Args:
            category: 'animals', 'birds', 'insects', or 'plants'
            
        Returns:
            Loaded model or None if not available
        """
        if category in ModelLoader._model_cache:
            return ModelLoader._model_cache[category]
        
        try:
            model_files = wildlife_config.get_model_files(category)
            model_path = str(model_files['model'])
            
            if Path(model_path).exists():
                model = joblib.load(model_path)
                ModelLoader._model_cache[category] = model
                return model
        except Exception as e:
            print(f"Error loading {category} model: {e}")
        
        return None
    
    @staticmethod
    def load_scaler(category: str) -> Optional[object]:
        """Load feature scaler for category"""
        if category in ModelLoader._scaler_cache:
            return ModelLoader._scaler_cache[category]
        
        try:
            model_files = wildlife_config.get_model_files(category)
            scaler_path = str(model_files['scaler'])
            
            if Path(scaler_path).exists():
                scaler = joblib.load(scaler_path)
                ModelLoader._scaler_cache[category] = scaler
                return scaler
        except Exception as e:
            print(f"Error loading {category} scaler: {e}")
        
        return None
    
    @staticmethod
    def load_feature_names(category: str) -> list:
        """Load feature names for category"""
        if category in ModelLoader._feature_cache:
            return ModelLoader._feature_cache[category]
        
        try:
            model_files = wildlife_config.get_model_files(category)
            features_path = str(model_files['feature_names'])
            
            if Path(features_path).exists():
                features = joblib.load(features_path)
                if isinstance(features, list) and features:
                    ModelLoader._feature_cache[category] = features
                    return features
        except Exception:
            pass
        
        # Fallback to default features
        default_features = FEATURE_SETS.get(category, [])
        ModelLoader._feature_cache[category] = default_features
        return default_features
    
    @staticmethod
    def load_metadata(category: str) -> Dict:
        """Load model metadata"""
        if category in ModelLoader._metadata_cache:
            return ModelLoader._metadata_cache[category]
        
        try:
            model_files = wildlife_config.get_model_files(category)
            metadata_path = str(model_files['metadata'])
            
            if Path(metadata_path).exists():
                metadata = joblib.load(metadata_path)
                if isinstance(metadata, dict):
                    ModelLoader._metadata_cache[category] = metadata
                    return metadata
        except Exception:
            pass
        
        return {}
    
    @staticmethod
    def load_occurrence_classifier(category: str) -> Optional[object]:
        """Load occurrence classifier for category"""
        if category in ModelLoader._occurrence_classifier_cache:
            return ModelLoader._occurrence_classifier_cache[category]
        
        try:
            model_files = wildlife_config.get_model_files(category)
            classifier_path = str(model_files['occurrence_classifier'])
            
            if Path(classifier_path).exists():
                classifier = joblib.load(classifier_path)
                ModelLoader._occurrence_classifier_cache[category] = classifier
                return classifier
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def load_occurrence_features(category: str) -> list:
        """Load occurrence classifier features"""
        if category in ModelLoader._occurrence_features_cache:
            return ModelLoader._occurrence_features_cache[category]
        
        try:
            model_files = wildlife_config.get_model_files(category)
            features_path = str(model_files['occurrence_features'])
            
            if Path(features_path).exists():
                features = joblib.load(features_path)
                if isinstance(features, list) and features:
                    ModelLoader._occurrence_features_cache[category] = features
                    return features
        except Exception:
            pass
        
        # Fallback to defaults
        default_features = OCCURRENCE_FEATURE_SETS.get(category, [])
        ModelLoader._occurrence_features_cache[category] = default_features
        return default_features
    
    @staticmethod
    def load_kmeans(category: str) -> Tuple[Optional[object], Optional[object]]:
        """Load KMeans model and scaler for category"""
        try:
            model_files = wildlife_config.get_model_files(category)
            
            kmeans_path = str(model_files.get('kmeans', ''))
            kmeans_scaler_path = str(model_files.get('kmeans_scaler', ''))
            
            kmeans = None
            scaler = None
            
            if Path(kmeans_path).exists():
                kmeans = joblib.load(kmeans_path)
            
            if Path(kmeans_scaler_path).exists():
                scaler = joblib.load(kmeans_scaler_path)
            
            ModelLoader._kmeans_cache[category] = kmeans
            ModelLoader._kmeans_scaler_cache[category] = scaler
            
            return kmeans, scaler
        except Exception:
            pass
        
        return None, None
    
    @staticmethod
    def load_kmeans_meta(category: str) -> Dict:
        """Load KMeans metadata"""
        if category in ModelLoader._kmeans_meta_cache:
            return ModelLoader._kmeans_meta_cache[category]
        
        try:
            model_files = wildlife_config.get_model_files(category)
            meta_path = str(model_files.get('kmeans_meta', ''))
            
            if Path(meta_path).exists():
                meta = joblib.load(meta_path)
                ModelLoader._kmeans_meta_cache[category] = meta
                return meta
        except Exception:
            pass
        
        return {}
    
    @staticmethod
    def clear_cache():
        """Clear all cached models (for testing/reload)"""
        ModelLoader._model_cache.clear()
        ModelLoader._scaler_cache.clear()
        ModelLoader._feature_cache.clear()
        ModelLoader._metadata_cache.clear()
        ModelLoader._occurrence_classifier_cache.clear()
        ModelLoader._occurrence_features_cache.clear()
        ModelLoader._occurrence_metadata_cache.clear()
        ModelLoader._kmeans_cache.clear()
        ModelLoader._kmeans_scaler_cache.clear()
        ModelLoader._kmeans_meta_cache.clear()
