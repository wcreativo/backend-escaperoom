from django.apps import AppConfig
from django.conf import settings
import os


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reservations'
    verbose_name = 'Reservations'

    def ready(self):
        """
        Initialize the scheduler when Django starts.
        Only start in background mode if not running as a dedicated worker.
        """
        # Don't start scheduler during migrations or in test mode
        if (
            'migrate' in os.sys.argv or 
            'makemigrations' in os.sys.argv or
            'test' in os.sys.argv or
            'start_scheduler' in os.sys.argv or
            os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('test')
        ):
            return
        
        # Only start background scheduler in development/production, not in worker mode
        if not getattr(settings, 'SCHEDULER_WORKER_MODE', False):
            try:
                from escape_rooms_backend.scheduler import get_scheduler
                get_scheduler()
            except Exception as e:
                # Log error but don't crash the app
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to start background scheduler: {e}")