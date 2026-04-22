"""
Input preprocessing and data cleaning utilities.
"""

import math
from typing import Any, Optional


def safe_float(value: Any, default: Optional[float] = None) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        result = float(value)
        return result if math.isfinite(result) else (default or 0.0)
    except (TypeError, ValueError):
        return default or 0.0


def safe_number(value: Any, default: float = 0.0) -> float:
    """Return finite float, otherwise fallback default."""
    try:
        num = float(value)
        if math.isfinite(num):
            return num
    except (TypeError, ValueError):
        pass
    return default


def safe_text(value: Any, default: str = 'Unknown') -> str:
    """Normalize missing/NaN text values for display and JSON safety."""
    if value is None:
        return default
    if isinstance(value, float) and not math.isfinite(value):
        return default
    text = str(value).strip()
    if not text or text.lower() in {'nan', 'none', 'null'}:
        return default
    return text


def safe_round(value: Any, decimals: int = 3) -> float:
    """Safely round a number"""
    try:
        num = float(value)
        if math.isfinite(num):
            return round(num, decimals)
    except (TypeError, ValueError):
        pass
    return 0.0


def normalize_species_text(value: str) -> str:
    """Normalize species name for matching"""
    if not isinstance(value, str):
        return ''
    return str(value).strip().lower()


def extract_numeric_fields(data: dict, field_names: list) -> dict:
    """
    Extract and convert numeric fields from request.
    
    Args:
        data: Request data dictionary
        field_names: List of field names to extract
        
    Returns:
        Dictionary of numeric values
    """
    result = {}
    for field in field_names:
        if field in data:
            result[field] = safe_float(data[field], 0.0)
    return result


def validate_coordinate_range(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude are in valid ranges.
    
    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        
    Returns:
        True if valid, False otherwise
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_temporal_values(day: int, month: int, year: int) -> bool:
    """
    Validate day, month, year are in valid ranges.
    
    Args:
        day: Day of month (1-31)
        month: Month of year (1-12)
        year: Year (1800-2030)
        
    Returns:
        True if valid, False otherwise
    """
    return (1 <= day <= 31) and (1 <= month <= 12) and (1800 <= year <= 2030)


def build_input_summary(input_data: dict, max_items: int = 12) -> list:
    """
    Build summary of input features for display.
    
    Args:
        input_data: Input feature dictionary
        max_items: Maximum items to return
        
    Returns:
        List of {feature, value} dicts
    """
    summary = []
    for i, (key, value) in enumerate(input_data.items()):
        if i >= max_items:
            break
        summary.append({
            'feature': key,
            'value': safe_round(value, 2)
        })
    return summary
