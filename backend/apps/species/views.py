from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from mongoengine.queryset.visitor import Q

from apps.common.pagination import build_paginated_response, parse_pagination_params
from apps.common.cache_utils import safe_cache_get, safe_cache_set
from apps.observations.models import Observation
from apps.species.models import Species


SPECIES_CACHE_TTL = getattr(settings, 'CACHE_TTL_SECONDS', 300)
SPECIES_NAME_CACHE_TTL = 24 * 3600


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


def _species_payload(species):
    return {
        'id': str(species.id),
        'name': species.name,
        'scientific_name': species.scientific_name,
        'category': species.category,
        'iucn_status': species.iucn_status,
    }


def _species_detail_payload(species):
    taxonomy = species.taxonomy
    return {
        'id': str(species.id),
        'name': species.name,
        'scientific_name': species.scientific_name,
        'category': species.category,
        'iucn_status': species.iucn_status,
        'description': species.description or '',
        'taxonomy': {
            'kingdom': taxonomy.kingdom,
            'phylum': taxonomy.phylum,
            'class_name': taxonomy.class_name,
            'order': taxonomy.order,
            'family': taxonomy.family,
            'genus': taxonomy.genus,
            'subspecies': taxonomy.subspecies,
        },
        'total_observations': species.total_observations,
    }


def _get_species_name_cache():
    cache_key = 'species:name-map'
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    species_name_cache = {
        str(doc['_id']): _normalize_text(doc.get('name'))
        for doc in Species._get_collection().find({}, {'name': 1})
    }
    safe_cache_set(cache_key, species_name_cache, timeout=SPECIES_NAME_CACHE_TTL)
    return species_name_cache


@require_http_methods(["GET"])
def species_list(request):
    try:
        category = _normalize_text(request.GET.get('category'))
        iucn_status = _normalize_text(request.GET.get('iucn_status')).upper()
        search = _normalize_text(request.GET.get('search'))
        sort = _normalize_text(request.GET.get('sort')) or 'name'
        offset, limit = parse_pagination_params(request, default_limit=20, max_limit=100)

        valid_categories = {'animals', 'birds', 'insects', 'plants'}
        valid_iucn = {'EX', 'EW', 'CR', 'EN', 'VU', 'NT', 'LC', 'DD', 'NE'}
        valid_sort_fields = {'name', '-name', 'scientific_name', '-scientific_name', 'iucn_status', '-iucn_status'}

        if category and category not in valid_categories:
            return JsonResponse({'error': 'Invalid category.'}, status=400)
        if iucn_status and iucn_status not in valid_iucn:
            return JsonResponse({'error': 'Invalid iucn_status.'}, status=400)
        if sort not in valid_sort_fields:
            return JsonResponse({'error': 'Invalid sort field.'}, status=400)

        cache_key = f'species:list:{category or "all"}:{iucn_status or "all"}:{search or "all"}:{sort}:{offset}:{limit}'
        cached = safe_cache_get(cache_key)
        if cached is not None:
            return JsonResponse(cached, status=200)

        query = Q()
        if category:
            query &= Q(category=category)
        if iucn_status:
            query &= Q(iucn_status=iucn_status)
        if search:
            query &= (Q(name__icontains=search) | Q(scientific_name__icontains=search))

        queryset = Species.objects(query).only('name', 'scientific_name', 'category', 'iucn_status').order_by(sort)
        total_count = queryset.count()
        results = [_species_payload(species) for species in queryset.skip(offset).limit(limit)]

        payload = build_paginated_response(results, total_count, offset, limit)
        safe_cache_set(cache_key, payload, timeout=SPECIES_CACHE_TTL)
        return JsonResponse(payload, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch species.'}, status=500)


@require_http_methods(["GET"])
def species_detail(request, species_id):
    try:
        species = Species.objects(id=species_id).only(
            'name', 'scientific_name', 'category', 'taxonomy', 'iucn_status', 'description', 'total_observations'
        ).first()
        if species is None:
            return JsonResponse({'error': 'Species not found.'}, status=404)
        return JsonResponse({'result': _species_detail_payload(species)}, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch species details.'}, status=500)


@require_http_methods(["GET"])
def species_observations(request, species_id):
    try:
        species = Species.objects(id=species_id).only('id', 'name').first()
        if species is None:
            return JsonResponse({'error': 'Species not found.'}, status=404)

        offset, limit = parse_pagination_params(request, default_limit=500, max_limit=500)

        queryset = Observation.objects(species=species.id).only('location', 'observed_at', 'species_name').order_by('-observed_at')
        total_count = queryset.count()

        results = []
        for observation in queryset.skip(offset).limit(limit):
            location = observation.location
            results.append(
                {
                    'lat': location.lat if location else None,
                    'lon': location.lon if location else None,
                    'date': observation.observed_at.isoformat() if observation.observed_at else None,
                }
            )

        return JsonResponse(build_paginated_response(results, total_count, offset, limit), status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch species observations.'}, status=500)


@require_http_methods(["GET"])
def species_photos(request, species_id):
    try:
        species = Species.objects(id=species_id).only('id', 'name', 'scientific_name').first()
        if species is None:
            return JsonResponse({'error': 'Species not found.'}, status=404)

        queryset = Observation.objects(species=species.id).only('image_url', 'source').order_by('-created_at').limit(50)
        results = []
        seen = set()

        for observation in queryset:
            image_url = _normalize_text(observation.image_url)
            if image_url and image_url not in seen:
                seen.add(image_url)
                results.append({'image_url': image_url, 'source': observation.source})

        if not results:
            slug = species.scientific_name.replace(' ', '+') if species.scientific_name else species.name.replace(' ', '+')
            results.append(
                {
                    'image_url': f'https://source.unsplash.com/featured/800x600/?wildlife,{slug}',
                    'source': 'external',
                }
            )

        return JsonResponse({'count': len(results), 'results': results}, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch species photos.'}, status=500)