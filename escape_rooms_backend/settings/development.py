"""
Development settings for escape_rooms_backend project.
"""

from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-hello-project-development-key-not-for-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Development CORS (more permissive)
CORS_ALLOW_ALL_ORIGINS = True

ALLOWED_HOSTS = ['*']

CORS_ALLOW_CREDENTIALS = True

# Database - Default to SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Development logging - Console only for simplicity
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
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
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'escape_rooms_backend': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'escape_rooms_backend.scheduler': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apscheduler': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

