import os
import logging
from pathlib import Path
from mongoengine import connect

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CORE_CONFIG_DIR = BASE_DIR / 'core' / 'config'


def _bool_env(name: str, default: str = 'False') -> bool:
    return os.getenv(name, default).lower() in {'1', 'true', 'yes', 'on'}


def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs from a local .env file into process env."""
    if not path.exists():
        return

    try:
        for raw_line in path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and (key not in os.environ or not os.environ.get(key)):
                os.environ[key] = value
    except Exception:
        # Keep startup resilient even if .env has formatting issues.
        pass


_load_env_file(CORE_CONFIG_DIR / '.env')

MONGO_URI = os.getenv('MONGO_URI', '')
if MONGO_URI:
    connect(
        host=MONGO_URI,
        alias='default',
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        retryWrites=True,
    )

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    # Retained for shared backend bootstrap/index initialization.
    'apps.observations.apps.ObservationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wildlife_project.urls'

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '300'))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'observations' / 'predictor' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-wildlife-conservation-secret-key-12345')
DEBUG = os.getenv('DEBUG', 'True').lower() in {'1', 'true', 'yes'}
ALLOWED_HOSTS = ['*']

USE_TZ = True
TIME_ZONE = 'UTC'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
}

# Project email (SMTP) configuration for OTP delivery.
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in {'1', 'true', 'yes'}
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in {'1', 'true', 'yes'}
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@koynawildlife.local')

MONGOENGINE_INDEX_AUTO_CREATE = _bool_env('MONGOENGINE_INDEX_AUTO_CREATE', 'True')
