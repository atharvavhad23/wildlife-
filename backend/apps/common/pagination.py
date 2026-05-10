def parse_pagination_params(request, default_limit=20, max_limit=100):
    try:
        offset = max(int(request.GET.get('offset', 0) or 0), 0)
    except (TypeError, ValueError):
        offset = 0

    try:
        limit = int(request.GET.get('limit', default_limit) or default_limit)
    except (TypeError, ValueError):
        limit = default_limit

    if limit < 1:
        limit = default_limit
    if limit > max_limit:
        limit = max_limit

    return offset, limit


def build_paginated_response(results, total_count, offset, limit):
    return {
        'count': total_count,
        'results': results,
        'offset': offset,
        'limit': limit,
    }