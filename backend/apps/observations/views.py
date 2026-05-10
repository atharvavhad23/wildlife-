from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.common.pagination import build_paginated_response, parse_pagination_params
from apps.common.cache_utils import safe_cache_get, safe_cache_set
from apps.observations.models import Observation
from apps.species.models import Species


def _normalize_text(value):
    if value is None:
        return ''
    text = str(value).strip()
    return '' if text.lower() in {'', 'nan', 'none', 'null'} else text


def _parse_int(value, default):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _species_name_map():
    cache_key = 'observations:species-name-map'
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    species_name_map = {
        str(doc['_id']): _normalize_text(doc.get('name'))
        for doc in Species._get_collection().find({}, {'name': 1})
    }
    safe_cache_set(cache_key, species_name_map, timeout=24 * 3600)
    return species_name_map


@require_http_methods(["GET"])
def observation_list(request):
    try:
        offset, limit = parse_pagination_params(request, default_limit=1000, max_limit=1000)

        species_name_filter = _normalize_text(request.GET.get('species'))
        min_lat = request.GET.get('min_lat')
        max_lat = request.GET.get('max_lat')
        min_lon = request.GET.get('min_lon')
        max_lon = request.GET.get('max_lon')

        query = Observation.objects
        if species_name_filter:
            query = query.filter(species_name__icontains=species_name_filter)

        bbox_active = all(value not in (None, '') for value in (min_lat, max_lat, min_lon, max_lon))
        if bbox_active:
            try:
                min_lat = float(min_lat)
                max_lat = float(max_lat)
                min_lon = float(min_lon)
                max_lon = float(max_lon)
            except (TypeError, ValueError):
                return JsonResponse({'error': 'Bounding box values must be numeric.'}, status=400)

            query = query.filter(geo_location__within_box=[(min_lon, min_lat), (max_lon, max_lat)])

        queryset = query.only('location', 'species_name', 'geo_location', 'species', 'observed_at').order_by('-observed_at')
        total_count = queryset.count()
        species_map = _species_name_map()
        results = []

        for observation in queryset.skip(offset).limit(limit):
            location = observation.location
            species_name = _normalize_text(observation.species_name)
            if not species_name and observation.species:
                species_name = species_map.get(str(observation.species.id), '')

            results.append(
                {
                    'id': str(observation.id),
                    'latitude': location.lat if location else None,
                    'longitude': location.lon if location else None,
                    'species_name': species_name,
                }
            )

        return JsonResponse(build_paginated_response(results, total_count, offset, limit), status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch observations.'}, status=500)