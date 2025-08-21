from .settings import *

# Development-specific settings
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Use SQLite for development if PostgreSQL is not available
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Disable CORS restrictions in development
CORS_ALLOW_ALL_ORIGINS = True

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'