import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings

from apps.observations.models import ObservationImageCache


def _media_root() -> Path:
    return Path(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR / 'media'))


def _media_url() -> str:
    return str(getattr(settings, 'MEDIA_URL', '/media/')).rstrip('/') + '/'


def _wildlife_dir() -> Path:
    path = _media_root() / 'wildlife_images'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(*parts: str) -> str:
    normalized = '::'.join(str(part).strip() for part in parts if str(part).strip())
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()


def _is_remote_url(value: str) -> bool:
    return str(value).startswith(('http://', 'https://'))


def _is_local_media_url(value: str) -> bool:
    value = str(value).strip()
    return value.startswith(_media_url()) or value.startswith('/media/')


def _local_path_from_url(local_url: str) -> Path:
    relative = str(local_url).strip().split('/media/', 1)[-1].lstrip('/')
    return _media_root() / relative


def _build_local_url(filename: str) -> str:
    return f"{_media_url()}wildlife_images/{filename}"


def _extension_from(source_url: str, content_type: str | None) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(';', 1)[0].strip().lower())
        if guessed:
            return guessed

    suffix = Path(urlparse(source_url).path).suffix.lower()
    if suffix in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
        return suffix
    return '.jpg'


def _load_cache_record(cache_key: str | None = None, *, source_url: str | None = None, occurrence_url: str | None = None):
    query = ObservationImageCache.objects
    if cache_key:
        record = query(cache_key=cache_key).first()
        if record:
            return record
    if source_url:
        record = query(source_url=source_url).first()
        if record:
            return record
    if occurrence_url:
        record = query(occurrence_url=occurrence_url).first()
        if record:
            return record
    return None


def _write_cached_image(source_url: str, cache_key: str, *, occurrence_url: str | None = None, species_name: str | None = None, category: str | None = None, source: str = 'inaturalist'):
    request = Request(source_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(request, timeout=10) as response:
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        data = response.read()

    file_name = f'{cache_key}{_extension_from(source_url, content_type)}'
    local_path = _wildlife_dir() / file_name
    local_path.write_bytes(data)
    local_url = _build_local_url(file_name)

    record = _load_cache_record(cache_key, source_url=source_url, occurrence_url=occurrence_url)
    now = datetime.utcnow()
    if record is None:
        record = ObservationImageCache(
            cache_key=cache_key,
            source_url=source_url,
            occurrence_url=occurrence_url,
            species_name=species_name,
            category=category,
            local_path=str(local_path),
            local_url=local_url,
            content_type=content_type,
            byte_size=len(data),
            source=source,
            created_at=now,
            updated_at=now,
            last_accessed_at=now,
        )
    else:
        record.source_url = source_url or record.source_url
        record.occurrence_url = occurrence_url or record.occurrence_url
        record.species_name = species_name or record.species_name
        record.category = category or record.category
        record.local_path = str(local_path)
        record.local_url = local_url
        record.content_type = content_type or record.content_type
        record.byte_size = len(data)
        record.source = source or record.source
        record.updated_at = now
        record.last_accessed_at = now
    record.save()
    return local_url


def resolve_cached_image(source_url: str | None, *, cache_key: str | None = None, occurrence_url: str | None = None, species_name: str | None = None, category: str | None = None, source: str = 'inaturalist') -> str | None:
    source_url = str(source_url or '').strip()
    cache_key = cache_key or _cache_key(source_url, occurrence_url or '', species_name or '', category or '')

    if source_url and _is_local_media_url(source_url):
        local_path = _local_path_from_url(source_url)
        return source_url if local_path.exists() else None

    record = _load_cache_record(cache_key, source_url=source_url, occurrence_url=occurrence_url)
    if record:
        record.last_accessed_at = datetime.utcnow()
        record.save()
        local_path = Path(record.local_path)
        if local_path.exists():
            return record.local_url

    if not source_url or not _is_remote_url(source_url):
        return None

    try:
        return _write_cached_image(
            source_url,
            cache_key,
            occurrence_url=occurrence_url,
            species_name=species_name,
            category=category,
            source=source,
        )
    except Exception:
        return None


def serve_cached_media_or_none(media_url: str | None):
    media_url = str(media_url or '').strip()
    if not media_url:
        return None

    local_path = _local_path_from_url(media_url) if _is_local_media_url(media_url) else None
    if local_path is None or not local_path.exists():
        return None
    return local_path