"""
Django settings for escape_rooms_backend project.

This file imports the appropriate settings based on the DJANGO_SETTINGS_MODULE
environment variable. Defaults to development settings.
"""

from decouple import config
import os

# Determine which settings to use
ENVIRONMENT = config('ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from config.settings.production import *
elif ENVIRONMENT == 'staging':
    from config.settings.production import *  # Use production settings for staging
else:
    from config.settings.development import *