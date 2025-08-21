"""
Development settings for escape_rooms_backend project.
"""

from .base import *

# Development specific settings
DEBUG = True

# Additional development apps (uncomment if you install django_extensions)
# INSTALLED_APPS += [
#     'django_extensions',  # Optional: for shell_plus and other dev tools
# ]

# Development database (can override base settings if needed)
# DATABASES['default']['OPTIONS'] = {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"}

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

# Development CORS (more permissive)
CORS_ALLOW_ALL_ORIGINS = True