import os
from pathlib import Path


class Settings:
    """
    Central configuration class for all environment variables.
    Use this in Django settings.py as a single source of truth.
    """

    @staticmethod
    def load_env():
        """Load environment variables from .env file."""
        env_file = Path(__file__).resolve().parent / '.env'
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = value
            except Exception:
                pass

    # Database
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/wildlife_db')

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Django
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

    # Email
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

    # App Info
    APP_NAME = os.getenv('APP_NAME', 'Wildlife Conservation Predictor')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')


# Load environment variables on import
Settings.load_env()

# Export singleton for use in Django settings
settings = Settings()
