from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.utils import timezone
from apps.reservations.models import Reservation
from apps.rooms.models import TimeSlot
import logging

logger = logging.getLogger(__name__)


def cancel_expired_reservations():
    """Cancel reservations that have expired (30+ minutes old and still pending)"""
    try:
        expired_reservations = Reservation.objects.filter(
            status='pending',
            expires_at__lt=timezone.now()
        )
        
        for reservation in expired_reservations:
            # Cancel the reservation
            reservation.status = 'cancelled'
            reservation.save()
            
            # Free up the time slot
            reservation.time_slot.status = 'active'
            reservation.time_slot.save()
            
            logger.info(f"Cancelled expired reservation {reservation.id}")
            
    except Exception as e:
        logger.error(f"Error cancelling expired reservations: {e}")


def start_scheduler():
    """Start the APScheduler"""
    scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)
    
    # Add job to run every minute
    scheduler.add_job(
        cancel_expired_reservations,
        'interval',
        minutes=1,
        id='cancel_expired_reservations',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler started")
    
    return scheduler