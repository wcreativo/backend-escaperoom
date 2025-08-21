from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from apps.reservations.models import Reservation
import logging

logger = logging.getLogger(__name__)


def cancel_expired_reservations():
    """
    Cancel reservations that have expired (30+ minutes old and still pending).
    This function runs atomically to ensure data consistency.
    """
    try:
        with transaction.atomic():
            # Find all expired reservations
            expired_reservations = Reservation.objects.select_related('time_slot').filter(
                status='pending',
                expires_at__lt=timezone.now()
            )
            
            cancelled_count = 0
            
            for reservation in expired_reservations:
                try:
                    # Use the model's cancel_reservation method for consistency
                    reservation.cancel_reservation()
                    cancelled_count += 1
                    logger.info(
                        f"Cancelled expired reservation {reservation.id} "
                        f"for {reservation.customer_name} - {reservation.room.name} "
                        f"on {reservation.time_slot.date} at {reservation.time_slot.time}"
                    )
                except Exception as e:
                    logger.error(f"Error cancelling reservation {reservation.id}: {e}")
                    continue
            
            if cancelled_count > 0:
                logger.info(f"Successfully cancelled {cancelled_count} expired reservations")
            else:
                logger.debug("No expired reservations found")
                
    except Exception as e:
        logger.error(f"Error in cancel_expired_reservations job: {e}")


def start_scheduler(blocking=False, config=None):
    """
    Start the APScheduler for automatic reservation cancellation.
    
    Args:
        blocking (bool): If True, uses BlockingScheduler (for dedicated worker process).
                        If False, uses BackgroundScheduler (for integration with Django app).
        config (dict): Optional scheduler configuration. If None, uses settings.SCHEDULER_CONFIG.
    
    Returns:
        scheduler: The started scheduler instance
    """
    try:
        # Use provided config or fall back to settings
        scheduler_config = config or settings.SCHEDULER_CONFIG
        
        # Choose scheduler type based on usage
        if blocking:
            scheduler = BlockingScheduler(scheduler_config)
        else:
            scheduler = BackgroundScheduler(scheduler_config)
        
        # Add job to run every minute
        scheduler.add_job(
            cancel_expired_reservations,
            'interval',
            minutes=1,
            id='cancel_expired_reservations',
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
            coalesce=True,    # Combine missed executions
        )
        
        scheduler.start()
        logger.info(f"APScheduler started ({'blocking' if blocking else 'background'} mode)")
        
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")
        raise


def stop_scheduler(scheduler):
    """
    Safely stop the scheduler.
    
    Args:
        scheduler: The scheduler instance to stop
    """
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("APScheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")


# Global scheduler instance for background mode
_background_scheduler = None


def get_scheduler():
    """Get the global background scheduler instance"""
    global _background_scheduler
    if _background_scheduler is None or not _background_scheduler.running:
        _background_scheduler = start_scheduler(blocking=False)
    return _background_scheduler