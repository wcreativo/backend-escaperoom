"""
Production settings for EscapeRooms.
"""
import os
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY environment variable is required in production')

# Production hosts
ALLOWED_HOSTS = [
    'escaperooms21.com',
    'www.escaperooms21.com',
    'escaperooms-backend',  # Allow internal Docker communication
    'localhost',             # Allow localhost access
    '127.0.0.1',            # Allow local IP access
    # Add your production domains here
]

# Database - Use environment variables for production (all required)
def get_required_env(var_name):
    """Get required environment variable or raise error"""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f'{var_name} environment variable is required in production')
    return value

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_required_env('DB_NAME'),
        'USER': get_required_env('DB_USER'),
        'PASSWORD': get_required_env('DB_PASSWORD'),
        'HOST': get_required_env('DB_HOST'),
        'PORT': get_required_env('DB_PORT'),
    }
}

# CORS settings - Restrict to specific origins in production
CORS_ALLOWED_ORIGINS = [
    "https://escaperooms21.com",
    "https://www.escaperooms21.com",
    "http://escaperooms-frontend:3000",  # Allow internal Docker communication
    "http://localhost:3000",              # Allow local development
]
CORS_ALLOW_CREDENTIALS = True

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# SSL settings (now using HTTPS)
# Disable SSL redirect for internal Docker communication
SECURE_SSL_REDIRECT = False  # Let nginx handle SSL termination
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Static files configuration for production
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for serving static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@escaperooms.com')