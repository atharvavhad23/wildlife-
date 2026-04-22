"""
Response schemas and standardization utilities.
"""

from typing import Any, Dict, Optional
import math


def sanitize_for_json(value: Any) -> Any:
    """
    Recursively remove NaN/Inf values so JSON parsing never fails.
    
    Args:
        value: Value to sanitize
        
    Returns:
        Sanitized value safe for JSON
    """
    if isinstance(value, dict):
        return {k: sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_for_json(v) for v in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


class ApiResponse:
    """Standardized API response wrapper"""
    
    @staticmethod
    def success(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
        """
        Return successful response.
        
        Args:
            data: Response data
            status_code: HTTP status code
            
        Returns:
            Standardized response dict
        """
        return {
            'status': 'success',
            'status_code': status_code,
            'data': sanitize_for_json(data)
        }
    
    @staticmethod
    def error(message: str, status_code: int = 400, details: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Return error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
            
        Returns:
            Standardized error response dict
        """
        response = {
            'status': 'error',
            'status_code': status_code,
            'message': message
        }
        if details:
            response['details'] = details
        return response


class PredictionResponse:
    """Prediction response schema"""
    
    @staticmethod
    def build(
        prediction: float,
        risk_level: str,
        status: str,
        recommendation: str,
        trend: Dict[str, Any],
        environmental_data: Dict[str, Any],
        input_summary: list = None,
        model_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Build standardized prediction response.
        
        Args:
            prediction: Predicted value
            risk_level: Risk assessment level
            status: Current status
            recommendation: Recommendation text
            trend: Trend analysis data
            environmental_data: Environmental factors
            input_summary: Summary of input data
            model_info: Model information
            
        Returns:
            Standardized prediction response
        """
        response = {
            'prediction': float(prediction),
            'risk_level': risk_level,
            'status': status,
            'recommendation': recommendation,
            'trend': trend,
            'environmental_data': sanitize_for_json(environmental_data),
        }
        
        if input_summary:
            response['input_summary'] = input_summary
        
        if model_info:
            response['model_info'] = model_info
        
        return sanitize_for_json(response)


class GalleryResponse:
    """Gallery/pagination response schema"""
    
    @staticmethod
    def build(
        rows: list,
        offset: int,
        total: int,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build standardized gallery response.
        
        Args:
            rows: Photo rows
            offset: Current offset
            total: Total items
            limit: Items per page
            
        Returns:
            Standardized gallery response
        """
        return {
            'rows': rows,
            'offset': offset,
            'total': total,
            'limit': limit,
            'has_more': (offset + len(rows)) < total if limit else False
        }


class DashboardResponse:
    """Dashboard response schema"""
    
    @staticmethod
    def build(
        prediction: float,
        model_type: str,
        risk_level: str,
        features_analyzed: int,
        recommendation: str,
        trend_info: Dict[str, Any] = None,
        environmental_factors: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Build standardized dashboard response.
        
        Args:
            prediction: Predicted value
            model_type: Type of model used
            risk_level: Risk level
            features_analyzed: Number of features used
            recommendation: Recommendation text
            trend_info: Trend information
            environmental_factors: Environmental data
            
        Returns:
            Standardized dashboard response
        """
        response = {
            'prediction': float(prediction),
            'model_type': model_type,
            'risk_level': risk_level,
            'features_analyzed': features_analyzed,
            'recommendation': recommendation,
        }
        
        if trend_info:
            response['trend'] = trend_info
        
        if environmental_factors:
            response['environmental_factors'] = sanitize_for_json(environmental_factors)
        
        return response
