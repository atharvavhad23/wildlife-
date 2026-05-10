from collections import defaultdict
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

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


def _cached_json(cache_key, builder, timeout=300):
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    payload = builder()
    safe_cache_set(cache_key, payload, timeout=timeout)
    return payload


@require_http_methods(["GET"])
def dashboard_view(request):
    try:
        def build_dashboard():
            species_collection = Species._get_collection()
            observation_collection = Observation._get_collection()

            total_species_count = species_collection.count_documents({})
            total_observations_count = observation_collection.count_documents({})

            category_pipeline = [
                {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
                {'$sort': {'_id': 1}},
            ]
            category_rows = list(species_collection.aggregate(category_pipeline))
            species_count_by_category = {category: 0 for category in ['animals', 'birds', 'insects', 'plants']}
            for row in category_rows:
                category = _normalize_text(row.get('_id'))
                if category:
                    species_count_by_category[category] = int(row.get('count', 0))

            recent_rows = list(
                observation_collection.find({}, {'location': 1, 'species_name': 1, 'observed_at': 1})
                .sort('observed_at', -1)
                .limit(10)
            )
            recent_observations = []
            for row in recent_rows:
                location = row.get('location') or {}
                recent_observations.append(
                    {
                        'latitude': location.get('lat'),
                        'longitude': location.get('lon'),
                        'species_name': _normalize_text(row.get('species_name')),
                        'date': row.get('observed_at').isoformat() if row.get('observed_at') else None,
                    }
                )

            return {
                'total_species_count': total_species_count,
                'total_observations_count': total_observations_count,
                'species_count_by_category': species_count_by_category,
                'recent_observations': recent_observations,
            }

        payload = _cached_json('analytics:dashboard', build_dashboard, timeout=300)
        return JsonResponse(payload, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch dashboard data.'}, status=500)


@require_http_methods(["GET"])
def cluster_list(request):
    try:
        grid_size = float(request.GET.get('grid_size', 0.25) or 0.25)
        grid_size = grid_size if grid_size > 0 else 0.25

        cache_key = f'analytics:clusters:{grid_size}'

        def build_clusters():
            pipeline = [
                {'$match': {'location.lat': {'$ne': None}, 'location.lon': {'$ne': None}}},
                {
                    '$project': {
                        'lat_bucket': {'$floor': {'$divide': ['$location.lat', grid_size]}},
                        'lon_bucket': {'$floor': {'$divide': ['$location.lon', grid_size]}},
                        'location': 1,
                    }
                },
                {
                    '$group': {
                        '_id': {'lat_bucket': '$lat_bucket', 'lon_bucket': '$lon_bucket'},
                        'count': {'$sum': 1},
                    }
                },
                {
                    '$project': {
                        '_id': 0,
                        'lat': {'$multiply': ['$_id.lat_bucket', grid_size]},
                        'lon': {'$multiply': ['$_id.lon_bucket', grid_size]},
                        'count': 1,
                    }
                },
                {'$sort': {'count': -1}},
            ]
            return list(Observation._get_collection().aggregate(pipeline))

        results = _cached_json(cache_key, build_clusters, timeout=300)
        return JsonResponse({'count': len(results), 'results': results}, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch clusters.'}, status=500)


@require_http_methods(["GET"])
def alerts_view(request):
    try:
        def build_alerts():
            species_collection = Species._get_collection()
            observation_collection = Observation._get_collection()

            species_rows = list(species_collection.find({}, {'name': 1, 'scientific_name': 1, 'iucn_status': 1}))
            observation_counts = defaultdict(int)
            for row in observation_collection.aggregate([{'$group': {'_id': '$species', 'count': {'$sum': 1}}}]):
                observation_counts[str(row.get('_id'))] = int(row.get('count', 0))

            alerts = []
            for row in species_rows:
                species_id = str(row['_id'])
                name = _normalize_text(row.get('name'))
                iucn_status = _normalize_text(row.get('iucn_status'))
                obs_count = observation_counts.get(species_id, 0)

                if iucn_status in {'CR', 'EN', 'VU'}:
                    alerts.append(
                        {
                            'species': name,
                            'alert_type': 'conservation_status',
                            'message': f'{name} is marked as {iucn_status}.',
                            'severity': 'high' if iucn_status in {'EN', 'VU'} else 'critical',
                        }
                    )
                elif obs_count <= 5:
                    alerts.append(
                        {
                            'species': name,
                            'alert_type': 'low_observation_count',
                            'message': f'{name} has only {obs_count} observations.',
                            'severity': 'medium',
                        }
                    )

                if len(alerts) >= 50:
                    break

            return alerts

        alerts = _cached_json('analytics:alerts', build_alerts, timeout=300)
        return JsonResponse({'count': len(alerts), 'results': alerts}, status=200)
    except Exception:
        return JsonResponse({'error': 'Failed to fetch alerts.'}, status=500)