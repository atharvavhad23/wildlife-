# Temporary file with clustering functions to add to views.py

# Global caches for clustering
_animals_clustering_cache = {}
_animals_species_cache = None
_clustering_lock = threading.Lock()

def _load_animals_data():
    """Load and cache animals CSV data."""
    global _animals_species_cache
    if _animals_species_cache is not None:
        return _animals_species_cache
    
    try:
        df = pd.read_csv(_project_file('Koyna_animals_final.csv'))
        _animals_species_cache = df
        return df
    except Exception:
        return pd.DataFrame()

def _perform_clustering(n_clusters=8):
    """
    Perform K-means clustering on animals by location + taxonomy.
    Returns: {cluster_id: [species_list], centers: [[lat, lon]], ...}
    """
    with _clustering_lock:
        cache_key = f'clusters_{n_clusters}'
        if cache_key in _animals_clustering_cache:
            return _animals_clustering_cache[cache_key]
    
    df = _load_animals_data()
    if df.empty:
        return {'error': 'No data available'}
    
    # Prepare features: geographic + taxonomic encoding
    df_clean = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])
    
    if len(df_clean) == 0:
        return {'error': 'No geographic data available'}
    
    # Feature engineering: location + class encoding
    df_features = df_clean.copy()
    
    # Encode categorical features
    class_mapping = {cls: i for i, cls in enumerate(df_features['class'].unique())}
    order_mapping = {ord: i for i, ord in enumerate(df_features['order'].unique())}
    
    df_features['class_enc'] = df_features['class'].map(class_mapping).fillna(0)
    df_features['order_enc'] = df_features['order'].map(order_mapping).fillna(0)
    
    # Select features for clustering
    features_for_clustering = df_features[[
        'decimalLatitude', 
        'decimalLongitude', 
        'class_enc',
        'order_enc',
        'year'
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
        'centers': kmeans.cluster_centers_.tolist(),
        'n_clusters': n_clusters,
        'total_species': len(df_clean),
    }
    
    # Group species by cluster
    for cluster_id in range(n_clusters):
        cluster_data = df_features[df_features['cluster'] == cluster_id]
        species_in_cluster = cluster_data['scientificName'].unique().tolist()
        result['clusters'][str(cluster_id)] = {
            'species_count': len(species_in_cluster),
            'animal_count': len(cluster_data),
            'center_lat': float(kmeans.cluster_centers_[cluster_id][0]),
            'center_lon': float(kmeans.cluster_centers_[cluster_id][1]),
            'species': species_in_cluster[:10],  # Top 10 for preview
        }
    
    with _clustering_lock:
        _animals_clustering_cache[cache_key] = result
    
    return result

def _get_species_detail(species_name):
    """
    Get detailed information about a specific species.
    Returns: species info + all related observations + images
    """
    df = _load_animals_data()
    if df.empty:
        return {'error': 'No data available'}
    
    # Filter by species name
    species_data = df[df['scientificName'].str.contains(species_name, case=False, na=False)]
    
    if species_data.empty:
        return {'error': 'Species not found'}
    
    # Aggregate information
    first_record = species_data.iloc[0]
    
    detail = {
        'scientificName': first_record.get('scientificName', 'Unknown'),
        'species': first_record.get('species', 'Unknown'),
        'class': first_record.get('class', 'Unknown'),
        'order': first_record.get('order', 'Unknown'),
        'family': first_record.get('family', 'Unknown'),
        'genus': first_record.get('genus', 'Unknown'),
        'kingdom': first_record.get('kingdom', 'Animalia'),
        'phylum': first_record.get('phylum', 'Unknown'),
        'observationCount': len(species_data),
        'locations': [],
        'occurrenceUrls': [],
        'dateRange': {
            'earliest': species_data['eventDate'].min() if 'eventDate' in species_data.columns else '',
            'latest': species_data['eventDate'].max() if 'eventDate' in species_data.columns else '',
        },
        'geographicRange': {
            'minLat': float(species_data['decimalLatitude'].min()) if 'decimalLatitude' in species_data.columns else 0,
            'maxLat': float(species_data['decimalLatitude'].max()) if 'decimalLatitude' in species_data.columns else 0,
            'minLon': float(species_data['decimalLongitude'].min()) if 'decimalLongitude' in species_data.columns else 0,
            'maxLon': float(species_data['decimalLongitude'].max()) if 'decimalLongitude' in species_data.columns else 0,
            'centerLat': float(species_data['decimalLatitude'].mean()) if 'decimalLatitude' in species_data.columns else 0,
            'centerLon': float(species_data['decimalLongitude'].mean()) if 'decimalLongitude' in species_data.columns else 0,
        },
        'conservationStatus': 'Not Evaluated',  # Could be enhanced with IUCN data
    }
    
    # Collect all observations
    for _, row in species_data.iterrows():
        loc = {
            'latitude': float(row.get('decimalLatitude', 0)),
            'longitude': float(row.get('decimalLongitude', 0)),
            'locality': str(row.get('locality', 'Unknown')),
            'eventDate': str(row.get('eventDate', '')),
            'occurrenceID': str(row.get('occurrenceID', '')),
        }
        detail['locations'].append(loc)
        detail['occurrenceUrls'].append(str(row.get('occurrenceID', '')))
    
    return detail

@require_http_methods(["GET"])
def animals_clustering_map(request):
    """Render clustering map page for animals."""
    return render(request, 'animals_clustering_map.html', {
        'clustering_api': '/api/animals/clustering/',
        'species_api': '/api/animals/species/',
    })

@require_http_methods(["GET"])
def get_animals_clustering(request):
    """API: Return clustering data for map."""
    try:
        n_clusters = int(request.GET.get('clusters', 8))
        n_clusters = max(3, min(20, n_clusters))  # Limit to 3-20 clusters
        
        result = _perform_clustering(n_clusters)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def get_species_detail(request):
    """API: Return detailed information about a species."""
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        
        detail = _get_species_detail(species_name)
        return JsonResponse(detail)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def species_detail_page(request):
    """Render species detail page with info + gallery."""
    species_name = request.GET.get('species', '').strip()
    if not species_name:
        return HttpResponse('Species parameter required', status=400)
    
    detail = _get_species_detail(species_name)
    if 'error' in detail:
        return HttpResponse(f"Species not found: {species_name}", status=404)
    
    return render(request, 'species_detail.html', {
        'species': detail,
        'species_name': species_name,
        'photos_api': '/api/animals/species-photos/',
    })

@require_http_methods(["GET"])
def get_species_photos(request):
    """API: Get paginated photos for a specific species."""
    try:
        species_name = str(request.GET.get('species', '')).strip()
        if not species_name:
            return JsonResponse({'error': 'Species name required'}, status=400)
        
        df = _load_animals_data()
        species_data = df[df['scientificName'].str.contains(species_name, case=False, na=False)]
        
        if species_data.empty:
            return JsonResponse({'error': 'Species not found'}, status=404)
        
        offset, limit = _parse_gallery_pagination(request)
        
        # Build photo data
        photos = []
        for _, row in species_data.iterrows():
            occurrence_url = str(row.get('occurrenceID', ''))
            if not occurrence_url.startswith('http'):
                continue
            
            title = str(row.get('scientificName', 'Unknown'))
            subtitle = str(row.get('locality', 'Koyna Region'))
            event_date = str(row.get('eventDate', ''))
            
            photos.append({
                'title': title[:120],
                'subtitle': subtitle[:80],
                'eventDate': event_date[:20],
                'occurrenceUrl': occurrence_url,
            })
        
        # Paginate
        total = len(photos)
        if offset >= total:
            return JsonResponse({
                'photos': [],
                'count': 0,
                'total': total,
                'offset': offset,
                'hasMore': False,
            })
        
        if limit is None:
            chunk = photos[offset:]
            next_offset = total
        else:
            chunk = photos[offset:offset + limit]
            next_offset = offset + len(chunk)
        
        # Resolve thumbnails in parallel
        occurrence_urls = [item.get('occurrenceUrl', '') for item in chunk]
        thumbnails = _resolve_thumbnails_parallel(occurrence_urls)
        
        result_photos = []
        for item in chunk:
            occurrence_url = item.get('occurrenceUrl', '')
            thumb = thumbnails.get(occurrence_url)
            result_photos.append({
                **item,
                'thumbnailUrl': thumb,
                'hasImage': bool(thumb),
            })
        
        return JsonResponse({
            'photos': result_photos,
            'count': len(result_photos),
            'total': total,
            'offset': offset,
            'nextOffset': next_offset,
            'hasMore': next_offset < total,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
