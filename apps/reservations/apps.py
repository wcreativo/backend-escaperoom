from django.apps import AppConfig
from django.conf import settings
import os


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reservations'
    verbose_name = 'Reservations'

    def ready(self):
        """
        App initialization.
        
        Note: Automatic scheduler startup has been disabled in favor of 
        database-level locking for reservation conflicts. The scheduler
        can still be run manually for cleanup tasks if needed.
        """
        # Scheduler auto-start disabled - using database constraints instead
        pass
        
        # Previous scheduler auto-start code (now disabled):
        # Don't start scheduler during migrations or in test mode
        # if (
        #     'migrate' in os.sys.argv or 
        #     'makemigrations' in os.sys.argv or
        #     'test' in os.sys.argv or
        #     'start_scheduler' in os.sys.argv or
        #     os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('test')
        # ):
        #     return
        # 
        # # Only start background scheduler in development/production, not in worker mode
        # if not getattr(settings, 'SCHEDULER_WORKER_MODE', False):
        #     try:
        #         from escape_rooms_backend.scheduler import get_scheduler
        #         get_scheduler()
        #     except Exception as e:
        #         # Log error but don't crash the app
        #         import logging
        #         logger = logging.getLogger(__name__)
        #         logger.error(f"Failed to start background scheduler: {e}")