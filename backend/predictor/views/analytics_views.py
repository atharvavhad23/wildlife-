"""
Analytics views: clustering, dashboards, reporting, and species analysis.
"""

import json
import threading
import pandas as pd
import numpy as np
import warnings
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

import wildlife_config
from predictor.services import safe_text, safe_number, safe_round, paginate_results
from predictor.constants import DEFAULT_N_CLUSTERS

warnings.filterwarnings('ignore')


# Caching for category data and clustering results
_clustering_cache = {'animals': {}, 'birds': {}, 'insects': {}, 'plants': {}}
_species_cache = {'animals': None, 'birds': None, 'insects': None, 'plants': None}
_clustering_lock = threading.Lock()


def _load_category_data(category='animals'):
    """Load and cache category CSV data."""
    global _species_cache
    if _species_cache[category] is not None:
        return _species_cache[category]
    
    files = {
        'animals': wildlife_config.RAW_ANIMALS_CSV,
        'birds': wildlife_config.RAW_BIRDS_CSV,
        'insects': wildlife_config.RAW_INSECTS_CSV,
        'plants': wildlife_config.RAW_PLANTS_CSV
    }
    
    try:
        df = pd.read_csv(str(files[category]))
        _species_cache[category] = df
        return df
    except Exception as e:
        print(f"Error loading {category} data: {e}")
        return pd.DataFrame()


def _filter_species_rows(df, species_name):
    """Filter DataFrame rows by species name (case-insensitive)"""
    if df.empty or not isinstance(species_name, str):
        return pd.DataFrame()
    
    species_name = species_name.strip().lower()
    
    if 'scientificName' in df.columns:
        match = df[df['scientificName'].str.lower().str.contains(species_name, na=False)]
        if not match.empty:
            return match
    
    if 'species' in df.columns:
        match = df[df['species'].str.lower().str.contains(species_name, na=False)]
        if not match.empty:
            return match
    
    return df[df.apply(
        lambda row: species_name in str(row).lower(),
        axis=1
    )]


def _perform_clustering(n_clusters=DEFAULT_N_CLUSTERS, category='animals'):
    """
    Perform K-means clustering by location + taxonomy.
    """
    with _clustering_lock:
        cache_key = f'clusters_{n_clusters}'
        if cache_key in _clustering_cache[category]:
            return _clustering_cache[category][cache_key]
    
    df = _load_category_data(category)
    if df.empty:
        return {'error': 'No data available'}
    
    # Prepare features: geographic + taxonomic encoding
    df_clean = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])
    
    if len(df_clean) == 0:
        return {'error': 'No geographic data available'}
    
    # Feature engineering: location + class encoding
    df_features = df_clean.copy()
    
    # Encode categorical features safely
    class_mapping = {cls: i for i, cls in enumerate(df_features['class'].unique())} if 'class' in df_features.columns else {}
    order_mapping = {ord: i for i, ord in enumerate(df_features['order'].unique())} if 'order' in df_features.columns else {}
    
    df_features['class_enc'] = df_features['class'].map(class_mapping).fillna(0) if 'class' in df_features.columns else 0
    df_features['order_enc'] = df_features['order'].map(order_mapping).fillna(0) if 'order' in df_features.columns else 0
    
    # Select features for clustering
    features_for_clustering = df_features[[
        'decimalLatitude', 
        'decimalLongitude', 
        'class_enc',
        'order_enc',
        'year' if 'year' in df_features.columns else 'eventDate'
    ]].fillna(0)
    
    # Standardize features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features_for_clustering)
    
    # Perform K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(features_scaled)
    
    df_features['cluster'] = cluster_labels
    
    # Build result
    result = {
        'clusters': {},
        'centers': [],
        'n_clusters': n_clusters,
        'total_species': len(df_clean),
    }
    
    # Group species by cluster
    for cluster_id in range(n_clusters):
        cluster_data = df_features[df_features['cluster'] == cluster_id]
        species_in_cluster = cluster_data['scientificName'].unique().tolist() if 'scientificName' in cluster_data.columns else []

        # Use geographic mean in original coordinate space for map display
        center_lat = float(cluster_data['decimalLatitude'].mean()) if len(cluster_data) else 0.0
        center_lon = float(cluster_data['decimalLongitude'].mean()) if len(cluster_data) else 0.0

        result['centers'].append([center_lat, center_lon])

        result['clusters'][str(cluster_id)] = {
            'species_count': len(species_in_cluster),
            'animal_count': len(cluster_data),
            'center_lat': center_lat,
            'center_lon': center_lon,
            'species': species_in_cluster[:10],
        }
    
    with _clustering_lock:
        _clustering_cache[category][cache_key] = result
    
    return result


def _get_species_detail(species_name, category='animals'):
    """
    Get detailed information about a specific species.
    """
    df = _load_category_data(category)
    if df.empty:
        return {'error': 'No data available'}
    
    # Filter by species name
    species_data = _filter_species_rows(df, species_name)
    
    if species_data.empty:
        return {'error': 'Species not found'}
    
    # Aggregate information
    first_record = species_data.iloc[0]
    
    detail = {
        'scientificName': safe_text(first_record.get('scientificName'), 'Unknown'),
        'species': safe_text(first_record.get('species'), 'Unknown'),
        'class': safe_text(first_record.get('class'), 'Unknown'),
        'order': safe_text(first_record.get('order'), 'Unknown'),
        'family': safe_text(first_record.get('family'), 'Unknown'),
        'genus': safe_text(first_record.get('genus'), 'Unknown'),
        'kingdom': safe_text(first_record.get('kingdom'), 'Animalia'),
        'phylum': safe_text(first_record.get('phylum'), 'Unknown'),
        'observationCount': len(species_data),
        'locations': [],
        'occurrenceUrls': [],
        'dateRange': {
            'earliest': safe_text(species_data['eventDate'].min(), '') if 'eventDate' in species_data.columns else '',
            'latest': safe_text(species_data['eventDate'].max(), '') if 'eventDate' in species_data.columns else '',
        },
        'geographicRange': {
            'minLat': safe_number(species_data['decimalLatitude'].min(), 0.0) if 'decimalLatitude' in species_data.columns else 0.0,
            'maxLat': safe_number(species_data['decimalLatitude'].max(), 0.0) if 'decimalLatitude' in species_data.columns else 0.0,
            'minLon': safe_number(species_data['decimalLongitude'].min(), 0.0) if 'decimalLongitude' in species_data.columns else 0.0,
            'maxLon': safe_number(species_data['decimalLongitude'].max(), 0.0) if 'decimalLongitude' in species_data.columns else 0.0,
            'centerLat': safe_number(species_data['decimalLatitude'].mean(), 0.0) if 'decimalLatitude' in species_data.columns else 0.0,
            'centerLon': safe_number(species_data['decimalLongitude'].mean(), 0.0) if 'decimalLongitude' in species_data.columns else 0.0,
        },
    }
    
    # Collect all observations
    for _, row in species_data.iterrows():
        loc = {
            'latitude': safe_number(row.get('decimalLatitude', 0), 0.0),
            'longitude': safe_number(row.get('decimalLongitude', 0), 0.0),
            'locality': safe_text(row.get('locality'), 'Unknown locality'),
            'eventDate': safe_text(row.get('eventDate'), ''),
            'occurrenceID': safe_text(row.get('occurrenceID'), ''),
        }
        detail['locations'].append(loc)
        detail['occurrenceUrls'].append(safe_text(row.get('occurrenceID'), ''))
    
    return detail


@csrf_exempt
@require_http_methods(["POST"])
def perform_clustering_api(request, category='animals'):
    """API endpoint to perform clustering"""
    try:
        n_clusters = DEFAULT_N_CLUSTERS
        
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                n_clusters = int(data.get('n_clusters', DEFAULT_N_CLUSTERS))
                n_clusters = max(2, min(n_clusters, 20))  # Constrain to 2-20
            except Exception:
                pass
        
        result = _perform_clustering(n_clusters, category)
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def get_species_detail_api(request, category='animals'):
    """API endpoint to get species detail"""
    try:
        species_name = request.GET.get('species', '')
        if not species_name:
            return JsonResponse({'error': 'species parameter required'}, status=400)
        
        result = _get_species_detail(species_name, category)
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def get_species_photos_api(request, category='animals'):
    """API endpoint to get photos for a species"""
    try:
        species_name = request.GET.get('species', '')
        if not species_name:
            return JsonResponse({'error': 'species parameter required'}, status=400)
        
        df = _load_category_data(category)
        if df.empty:
            return JsonResponse({'error': 'No data available'}, status=400)
        
        # Filter by species name
        species_data = _filter_species_rows(df, species_name)
        
        if species_data.empty:
            return JsonResponse({'error': 'Species not found'}, status=400)
        
        # Build photo list
        photos = []
        for _, row in species_data.iterrows():
            occurrence_url = safe_text(row.get('occurrenceID'), '')
            if occurrence_url.startswith('http'):
                photos.append({
                    'occurrenceID': occurrence_url,
                    'scientificName': safe_text(row.get('scientificName'), 'Unknown'),
                    'locality': safe_text(row.get('locality'), ''),
                    'eventDate': safe_text(row.get('eventDate'), ''),
                })
        
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 20))
        
        paginated_photos, total = paginate_results(photos, offset, limit)
        
        return JsonResponse({
            'photos': paginated_photos,
            'offset': offset,
            'total': total,
            'limit': limit,
            'hasMore': (offset + limit) < total,
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def get_gallery_photos_by_category(request, category='animals'):
    """Gallery endpoint: photos by category"""
    try:
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 20))
        
        df = _load_category_data(category)
        
        if df.empty:
            return JsonResponse({
                'photos': [],
                'offset': offset,
                'total': 0,
                'limit': limit,
                'hasMore': False,
            })
        
        # Filter rows with occurrence data
        if 'occurrenceID' in df.columns:
            df_with_photos = df[df['occurrenceID'].notna()].copy()
            df_with_photos = df_with_photos[df_with_photos['occurrenceID'].astype(str).str.startswith('http', na=False)]
        else:
            df_with_photos = pd.DataFrame()
        
        if df_with_photos.empty:
            return JsonResponse({
                'photos': [],
                'offset': offset,
                'total': 0,
                'limit': limit,
                'hasMore': False,
            })
        
        # Build photo rows
        photos = []
        for _, row in df_with_photos.iterrows():
            photos.append({
                'title': safe_text(row.get('scientificName'), 'Unknown Species'),
                'subtitle': safe_text(row.get('locality'), 'Koyna Region'),
                'eventDate': safe_text(row.get('eventDate'), ''),
                'occurrenceUrl': safe_text(row.get('occurrenceID'), ''),
            })
        
        # Paginate
        paginated_photos, total = paginate_results(photos, offset, limit)
        
        return JsonResponse({
            'photos': paginated_photos,
            'offset': offset,
            'total': total,
            'limit': limit,
            'hasMore': (offset + limit) < total,
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_cluster_heatmap(request):
    """Get cluster heatmap data for all species"""
    try:
        category = request.GET.get('category', 'animals')
        result = _perform_clustering(DEFAULT_N_CLUSTERS, category)
        
        if 'error' in result:
            return JsonResponse(result, status=400)
        
        return JsonResponse({
            'clusters': result['clusters'],
            'centers': result['centers'],
            'n_clusters': result['n_clusters'],
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_cluster_details(request):
    """Get detailed information about a specific cluster"""
    try:
        category = request.GET.get('category', 'animals')
        cluster_id = request.GET.get('cluster_id', '')
        
        result = _perform_clustering(DEFAULT_N_CLUSTERS, category)
        
        if 'error' in result:
            return JsonResponse(result, status=400)
        
        if cluster_id not in result['clusters']:
            return JsonResponse({'error': 'Cluster not found'}, status=400)
        
        cluster_detail = result['clusters'][cluster_id]
        
        return JsonResponse({
            'cluster_id': cluster_id,
            'species_count': cluster_detail['species_count'],
            'animal_count': cluster_detail['animal_count'],
            'center': {
                'lat': cluster_detail['center_lat'],
                'lon': cluster_detail['center_lon'],
            },
            'species': cluster_detail['species'],
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_cluster_timeline(request):
    """Get temporal distribution of observations in cluster"""
    try:
        category = request.GET.get('category', 'animals')
        cluster_id = request.GET.get('cluster_id', '')
        
        df = _load_category_data(category)
        if df.empty:
            return JsonResponse({'error': 'No data available'}, status=400)
        
        # For simplicity, return yearly distribution
        if 'year' in df.columns:
            yearly_dist = df['year'].value_counts().sort_index()
            return JsonResponse({
                'timeline': yearly_dist.to_dict(),
                'labels': yearly_dist.index.tolist(),
                'values': yearly_dist.values.tolist(),
            })
        
        return JsonResponse({'timeline': {}})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_seasonal_activity(request):
    """Get seasonal activity distribution"""
    try:
        category = request.GET.get('category', 'animals')
        
        df = _load_category_data(category)
        if df.empty:
            return JsonResponse({'error': 'No data available'}, status=400)
        
        # Extract month from eventDate if available
        if 'eventDate' in df.columns:
            df['month'] = pd.to_datetime(df['eventDate'], errors='coerce').dt.month
            monthly_dist = df['month'].value_counts().sort_index()
            
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            return JsonResponse({
                'seasonal_data': monthly_dist.to_dict(),
                'labels': [month_names[int(m)-1] if 1 <= m <= 12 else f'M{m}' for m in monthly_dist.index],
                'values': monthly_dist.values.tolist(),
            })
        
        return JsonResponse({'seasonal_data': {}})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_conservation_alerts(request):
    """Get conservation alerts based on species status"""
    try:
        category = request.GET.get('category', 'animals')
        
        df = _load_category_data(category)
        if df.empty:
            return JsonResponse({'alerts': []})
        
        # Simple alert logic based on observation frequency
        species_counts = df['scientificName'].value_counts() if 'scientificName' in df.columns else pd.Series()
        
        alerts = []
        for species, count in species_counts.head(10).items():
            if count < 5:
                alert_level = 'Critical'
                message = f"{species}: Very few observations ({count})"
            elif count < 15:
                alert_level = 'Warning'
                message = f"{species}: Limited observations ({count})"
            else:
                alert_level = 'Info'
                message = f"{species}: Stable population ({count} observations)"
            
            alerts.append({
                'species': species,
                'level': alert_level,
                'message': message,
                'count': int(count),
            })
        
        return JsonResponse({'alerts': alerts})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_top_observers(request):
    """Get top observers/contributors"""
    try:
        category = request.GET.get('category', 'animals')
        
        df = _load_category_data(category)
        if df.empty:
            return JsonResponse({'observers': []})
        
        # Try to get observer data
        if 'observer' in df.columns:
            observer_counts = df['observer'].value_counts().head(10)
            observers = [
                {'name': observer, 'observations': int(count)}
                for observer, count in observer_counts.items()
            ]
        else:
            observers = []
        
        return JsonResponse({'observers': observers})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET", "POST"])
def wildlife_dashboard(request):
    """Main wildlife dashboard with aggregated analytics"""
    if request.method == "GET":
        return render(request, 'dashboard.html', {
            'species_label': 'Wildlife',
        })
    
    try:
        category = request.GET.get('category', 'animals')
        
        df = _load_category_data(category)
        if df.empty:
            return JsonResponse({'error': 'No data available'}, status=400)
        
        # Build dashboard statistics
        total_observations = len(df)
        unique_species = df['scientificName'].nunique() if 'scientificName' in df.columns else 0
        geographic_coverage = df[['decimalLatitude', 'decimalLongitude']].drop_duplicates().shape[0] if 'decimalLatitude' in df.columns else 0
        
        # Get clustering data
        clustering_result = _perform_clustering(DEFAULT_N_CLUSTERS, category)
        
        dashboard_data = {
            'category': category,
            'statistics': {
                'total_observations': int(total_observations),
                'unique_species': int(unique_species),
                'geographic_locations': int(geographic_coverage),
                'clusters': clustering_result.get('n_clusters', 0),
            },
            'clustering': clustering_result,
        }
        
        return JsonResponse(dashboard_data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
