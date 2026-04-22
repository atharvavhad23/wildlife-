"""
Request validation schemas.
"""

import json
from typing import Any, Dict

class ValidationError(Exception):
    """Custom validation error"""
    pass


class PredictionRequestSchema:
    """Validates prediction request payloads"""
    
    REQUIRED_FIELDS = {
        'animals': [
            'coordinateUncertaintyInMeters', 'month', 'year', 'day', 'decade',
            'lat_grid', 'lon_grid', 'phylum_enc', 'class_enc', 'order_enc',
            'family_enc', 'taxonRank_enc', 'basisOfRecord_enc', 'season_enc',
            'species_richness'
        ],
        'birds': [
            'coordinateUncertaintyInMeters', 'day', 'month', 'year', 'decade',
            'order_enc', 'family_enc', 'taxonRank_enc', 'basisOfRecord_enc',
            'season_enc', 'lat_grid', 'lon_grid', 'species_richness'
        ],
        'insects': [
            'coordinateUncertaintyInMeters', 'day', 'month', 'year', 'decade',
            'order_enc', 'family_enc', 'taxonRank_enc', 'basisOfRecord_enc',
            'season_enc', 'lat_grid', 'lon_grid', 'species_richness'
        ],
        'plants': [
            'coordinateUncertaintyInMeters', 'day', 'month', 'year', 'decade',
            'season_enc', 'lat_grid', 'lon_grid', 'species_richness',
            'order_enc', 'family_enc', 'class_enc', 'taxonRank_enc', 'basisOfRecord_enc'
        ]
    }

    @staticmethod
    def validate(data: Dict[str, Any], category: str) -> Dict[str, Any]:
        """
        Validate prediction request data.
        
        Args:
            data: Request data dictionary
            category: Category name (animals/birds/insects/plants)
            
        Returns:
            Validated data
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        
        if category not in PredictionRequestSchema.REQUIRED_FIELDS:
            raise ValidationError(f"Invalid category: {category}")
        
        # Validate required fields
        required = PredictionRequestSchema.REQUIRED_FIELDS[category]
        for field in required:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
            
            # Check if it's a number
            try:
                float(data[field])
            except (ValueError, TypeError):
                raise ValidationError(f"Field '{field}' must be a number, got: {data[field]}")
        
        return data


class EmailOTPSchema:
    """Validates OTP email requests"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email/OTP request"""
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        
        email = data.get('email', '').strip().lower()
        if not email or '@' not in email:
            raise ValidationError("Valid email is required")
        
        purpose = data.get('purpose', 'auth').strip().lower() or 'auth'
        
        return {
            'email': email,
            'purpose': purpose
        }


class OTPVerificationSchema:
    """Validates OTP verification requests"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate OTP verification request"""
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        
        email = data.get('email', '').strip().lower()
        if not email or '@' not in email:
            raise ValidationError("Valid email is required")
        
        purpose = data.get('purpose', 'auth').strip().lower() or 'auth'
        
        otp_code = data.get('otp', '').strip()
        if not otp_code:
            raise ValidationError("OTP code is required")
        
        return {
            'email': email,
            'purpose': purpose,
            'otp': otp_code
        }


class ClusteringRequestSchema:
    """Validates clustering API requests"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate clustering request"""
        n_clusters = data.get('n_clusters', 8)
        dataset = data.get('dataset', 'animals')
        
        try:
            n_clusters = int(n_clusters)
            if n_clusters < 2 or n_clusters > 50:
                raise ValidationError("n_clusters must be between 2 and 50")
        except (ValueError, TypeError):
            raise ValidationError("n_clusters must be an integer")
        
        if dataset not in ['animals', 'birds', 'insects', 'plants']:
            raise ValidationError(f"Invalid dataset: {dataset}")
        
        return {
            'n_clusters': n_clusters,
            'dataset': dataset
        }
