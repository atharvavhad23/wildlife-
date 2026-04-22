"""
Output postprocessing and response formatting utilities.
"""

import math
from typing import Any, Dict, List, Optional
from predictor.services.preprocessing import safe_float, safe_text, safe_round


def model_display_name(category: str) -> str:
    """Get display name for model"""
    display_names = {
        'animals': 'Wildlife Animal Classification',
        'birds': 'Bird Species Identification',
        'insects': 'Insect Species Classification',
        'plants': 'Plant Species Identification',
    }
    return display_names.get(category, category.title())


def risk_level_from_prediction(prediction: float, model_type: str = 'animals') -> str:
    """
    Determine risk level based on prediction value.
    
    Args:
        prediction: Predicted value
        model_type: Type of model
        
    Returns:
        Risk level string (Low, Medium, High, Critical)
    """
    prediction = safe_float(prediction, 0.0)
    
    if prediction < 0.25:
        return 'Low'
    elif prediction < 0.50:
        return 'Medium'
    elif prediction < 0.75:
        return 'High'
    else:
        return 'Critical'


def status_from_risk(risk_level: str) -> str:
    """Determine status text from risk level"""
    status_map = {
        'Low': 'Stable - No immediate conservation action required',
        'Medium': 'Caution - Monitor population changes',
        'High': 'Alert - Conservation measures recommended',
        'Critical': 'Emergency - Immediate intervention needed',
    }
    return status_map.get(risk_level, 'Unknown')


def recommendation_from_risk(risk_level: str, category: str) -> str:
    """Get conservation recommendation based on risk"""
    recommendations = {
        'Low': f'Continue regular monitoring of {category} populations.',
        'Medium': f'Increase monitoring frequency for {category} in the region.',
        'High': f'Implement targeted conservation programs for {category}.',
        'Critical': f'Urgent conservation intervention required for {category}.',
    }
    return recommendations.get(risk_level, 'Monitor population status')


def extract_feature_importance(
    model: Optional[object],
    feature_names: list,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Extract feature importance from model.
    
    Args:
        model: Trained model with feature importance
        feature_names: List of feature names
        top_n: Number of top features to return
        
    Returns:
        List of {feature, importance, rank} dicts
    """
    if not model or not hasattr(model, 'feature_importances_'):
        return []
    
    try:
        importances = model.feature_importances_
        if not isinstance(importances, (list, tuple)):
            return []
        
        # Create list of (feature, importance) tuples
        feature_imp = list(zip(feature_names, importances))
        
        # Sort by importance (descending)
        feature_imp.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        result = []
        for rank, (feature, importance) in enumerate(feature_imp[:top_n], 1):
            result.append({
                'feature': feature,
                'importance': safe_round(importance, 4),
                'rank': rank
            })
        
        return result
    except Exception:
        return []


def build_gallery_row_from_dict(
    species: str,
    photo_url: str,
    count: int = 1,
    location: str = 'Unknown'
) -> Dict[str, Any]:
    """Build single gallery row"""
    return {
        'species': safe_text(species),
        'photo_url': safe_text(photo_url),
        'count': max(0, int(count)) if isinstance(count, (int, float)) else 0,
        'location': safe_text(location),
    }


def build_dashboard_stat(label: str, value: Any, unit: str = '') -> Dict[str, str]:
    """Build dashboard statistic widget"""
    return {
        'label': label,
        'value': str(safe_round(value, 2) if isinstance(value, (int, float)) else value),
        'unit': unit
    }


def format_trend_data(
    trend_values: list,
    trend_percentages: list = None,
    trend_labels: list = None
) -> Dict[str, Any]:
    """
    Format trend analysis data for API response.
    
    Args:
        trend_values: List of trend values
        trend_percentages: List of percentage changes
        trend_labels: List of period labels
        
    Returns:
        Formatted trend dict
    """
    trend = {
        'values': [safe_round(v, 2) for v in trend_values] if trend_values else [],
    }
    
    if trend_percentages:
        trend['percentages'] = [safe_round(p, 2) for p in trend_percentages]
    
    if trend_labels:
        trend['labels'] = [safe_text(l) for l in trend_labels]
    
    return trend


def format_environmental_data(env_data: dict) -> Dict[str, Any]:
    """
    Format environmental data for response.
    
    Args:
        env_data: Raw environmental data
        
    Returns:
        Formatted environmental data
    """
    if not isinstance(env_data, dict):
        return {}
    
    formatted = {}
    for key, value in env_data.items():
        if isinstance(value, (int, float)):
            formatted[key] = safe_round(value, 2)
        elif isinstance(value, (list, dict)):
            formatted[key] = value
        else:
            formatted[key] = safe_text(value)
    
    return formatted


def paginate_results(
    items: list,
    offset: int = 0,
    limit: int = 20
) -> tuple:
    """
    Paginate results list.
    
    Args:
        items: List of items to paginate
        offset: Starting offset
        limit: Items per page
        
    Returns:
        (paginated_items, total_count)
    """
    if not isinstance(items, list):
        return [], 0
    
    offset = max(0, int(offset))
    limit = max(1, int(limit))
    
    total = len(items)
    end_idx = offset + limit
    
    return items[offset:end_idx], total
