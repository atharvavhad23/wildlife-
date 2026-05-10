from django.core.cache import cache


def safe_cache_get(key, default=None):
    try:
        return cache.get(key, default)
    except Exception:
        return default


def safe_cache_set(key, value, timeout=None):
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        return False
    return True