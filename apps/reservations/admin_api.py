from ninja import Router, Query
from ninja.errors import HttpError
from typing import Optional
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from django.db import transaction
from .models import Reservation
from .schemas import (
    ReservationSchema, 
    ReservationUpdateSchema,
    ReservationListSchema,
    ReservationStatsSchema,
    ReservationDateTimeUpdateSchema,
    ReservationPeopleUpdateSchema
)
from apps.authentication.middleware import jwt_auth

router = Router()



@router.get("/reservations/", auth=jwt_auth)
def list_reservations_admin(request):
    """
    List all reservations with filtering and pagination (admin only)
    
    Filters:
    - status: Filter by reservation status (pending, paid, cancelled)
    - room_id: Filter by specific room
    - search: Search in customer name, email, or phone
    - date_from: Filter reservations from this date (YYYY-MM-DD)
    - date_to: Filter reservations to this date (YYYY-MM-DD)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Parse parameters manually to avoid Django Ninja validation issues
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
        
    try:
        per_page = int(request.GET.get('per_page', 20))
        if per_page < 1:
            per_page = 20
        elif per_page > 100:
            per_page = 100
    except (ValueError, TypeError):
        per_page = 20
        
    status = request.GET.get('status', None)
    if status == '':
        status = None
        
    try:
        room_id = request.GET.get('room_id', None)
        if room_id:
            room_id = int(room_id)
    except (ValueError, TypeError):
        room_id = None
        
    search = request.GET.get('search', None)
    if search == '':
        search = None
        
    date_from = request.GET.get('date_from', None)
    if date_from == '':
        date_from = None
        
    date_to = request.GET.get('date_to', None)
    if date_to == '':
        date_to = None
    
    # New parameter for filtering by time period (active/past)
    time_filter = request.GET.get('time_filter', None)
    if time_filter == '':
        time_filter = None
    
    logger.info(f"Admin reservations request - page: {page}, per_page: {per_page}, status: {status}, time_filter: {time_filter}")
    
    try:
        logger.info(f"Admin reservations request - page: {page}, per_page: {per_page}")
        
        queryset = Reservation.objects.select_related('room', 'time_slot').all()
        logger.info(f"Initial queryset count: {queryset.count()}")
        
        # Log some sample data to see what we're working with
        if queryset.exists():
            sample_reservation = queryset.first()
            logger.info(f"Sample reservation data: id={sample_reservation.id}, "
                       f"room={sample_reservation.room.name if sample_reservation.room else 'None'}, "
                       f"time_slot={sample_reservation.time_slot.id if sample_reservation.time_slot else 'None'}, "
                       f"status={sample_reservation.status}")
    except Exception as e:
        logger.error(f"Error in initial query: {str(e)}")
        raise HttpError(500, f"Database error: {str(e)}")
    
    # Apply filters
    if status:
        if status not in ['pending', 'paid', 'cancelled']:
            raise HttpError(400, "Invalid status. Must be one of: pending, paid, cancelled")
        queryset = queryset.filter(status=status)
    
    if room_id:
        queryset = queryset.filter(room_id=room_id)
    
    if search:
        queryset = queryset.filter(
            Q(customer_name__icontains=search) |
            Q(customer_email__icontains=search) |
            Q(customer_phone__icontains=search)
        )
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            queryset = queryset.filter(time_slot__date__gte=from_date)
        except ValueError:
            raise HttpError(400, "Invalid date_from format. Use YYYY-MM-DD")
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            queryset = queryset.filter(time_slot__date__lte=to_date)
        except ValueError:
            raise HttpError(400, "Invalid date_to format. Use YYYY-MM-DD")
    
    # Filter by time period (active = today and future, past = before today)
    from datetime import date as date_class
    today = date_class.today()
    
    if time_filter == 'active':
        # Reservations from today onwards
        queryset = queryset.filter(time_slot__date__gte=today)
        # Order ascending (nearest first)
        queryset = queryset.order_by('time_slot__date', 'time_slot__time')
    elif time_filter == 'past':
        # Reservations before today
        queryset = queryset.filter(time_slot__date__lt=today)
        # Order descending (most recent first)
        queryset = queryset.order_by('-time_slot__date', '-time_slot__time')
    else:
        # No time filter - show all, ordered by date ascending (nearest first)
        queryset = queryset.order_by('time_slot__date', 'time_slot__time')
    
    # Paginate results
    try:
        paginator = Paginator(queryset, per_page)
        logger.info(f"Paginator created - total: {paginator.count}, pages: {paginator.num_pages}")
        
        if page > paginator.num_pages and paginator.num_pages > 0:
            logger.warning(f"Page {page} requested but only {paginator.num_pages} pages available")
            raise HttpError(404, "Page not found")
        
        page_obj = paginator.get_page(page)
        logger.info(f"Page object created - items: {len(page_obj)}")
        
        # Try to serialize each reservation to catch data issues
        reservations_list = []
        for i, reservation in enumerate(page_obj):
            try:
                # Handle corrupted data gracefully with safe getters
                def safe_get(obj, attr, default=None):
                    try:
                        value = getattr(obj, attr, default)
                        return value if value is not None else default
                    except:
                        return default
                
                def safe_format_date(time_slot):
                    try:
                        if time_slot and hasattr(time_slot, 'date') and time_slot.date:
                            return time_slot.date.strftime('%Y-%m-%d')
                    except:
                        pass
                    return None
                
                def safe_format_time(time_slot):
                    try:
                        if time_slot and hasattr(time_slot, 'time') and time_slot.time:
                            return time_slot.time.strftime('%H:%M:%S')
                    except:
                        pass
                    return None
                
                reservation_data = {
                    "id": safe_get(reservation, 'id', 0),
                    "room_id": safe_get(reservation.room, 'id') if reservation.room else None,
                    "room_name": safe_get(reservation.room, 'name', "Sala no disponible") if reservation.room else "Sala no disponible",
                    "customer_name": safe_get(reservation, 'customer_name', "N/A"),
                    "customer_email": safe_get(reservation, 'customer_email', "N/A"),
                    "customer_phone": safe_get(reservation, 'customer_phone', "N/A"),
                    "date": safe_format_date(reservation.time_slot),
                    "time": safe_format_time(reservation.time_slot),
                    "num_people": safe_get(reservation, 'num_people', 0),
                    "total_price": float(safe_get(reservation, 'total_price', 0)),
                    "status": safe_get(reservation, 'status', "unknown"),
                    "created_at": safe_get(reservation, 'created_at'),
                    "expires_at": safe_get(reservation, 'expires_at')
                }
                reservations_list.append(reservation_data)
            except Exception as e:
                logger.error(f"Error serializing reservation {reservation.id}: {str(e)}")
                logger.error(f"Reservation data: room={reservation.room}, time_slot={reservation.time_slot}")
                # Create a minimal safe record for corrupted data
                try:
                    safe_record = {
                        "id": getattr(reservation, 'id', 0),
                        "room_id": None,
                        "room_name": "DATOS CORRUPTOS",
                        "customer_name": "DATOS CORRUPTOS",
                        "customer_email": "DATOS CORRUPTOS",
                        "customer_phone": "DATOS CORRUPTOS",
                        "date": None,
                        "time": None,
                        "num_people": 0,
                        "total_price": 0.0,
                        "status": "corrupted",
                        "created_at": None,
                        "expires_at": None
                    }
                    reservations_list.append(safe_record)
                    logger.warning(f"Added corrupted reservation {reservation.id} with safe defaults")
                except:
                    logger.error(f"Completely skipping reservation {reservation.id} - too corrupted")
                    continue
        
        response_data = {
            "reservations": reservations_list,
            "total": paginator.count,
            "page": page,
            "per_page": per_page,
            "total_pages": paginator.num_pages
        }
        
        logger.info(f"Successfully returned {len(reservations_list)} reservations")
        return response_data
        
    except Exception as e:
        logger.error(f"Error in pagination/serialization: {str(e)}")
        raise HttpError(500, f"Error processing reservations: {str(e)}")


# IMPORTANT: More specific routes must come BEFORE more general routes
# /reservations/{id}/reschedule/ must be before /reservations/{id}/
@router.patch("/reservations/{reservation_id}/reschedule/", response=ReservationSchema, auth=jwt_auth)
def update_reservation_datetime(request, reservation_id: int, payload: ReservationDateTimeUpdateSchema):
    """
    Update reservation date and time (admin only)
    
    Allows changing the reservation to a different date/time slot.
    Automatically frees the old time slot and reserves the new one.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from apps.rooms.models import TimeSlot
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Get new date and time from payload
    new_date_str = payload.date
    new_time_str = payload.time
    
    # Parse date and time
    try:
        new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        new_time = datetime.strptime(new_time_str, "%H:%M").time()
    except ValueError:
        raise HttpError(400, "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time")
    
    # Validate that the new date/time is not in the past
    from datetime import date as date_class
    today = date_class.today()
    
    if new_date < today:
        raise HttpError(400, "Cannot reschedule to a past date")
    
    if new_date == today:
        now = timezone.now()
        minimum_time = now + timezone.timedelta(hours=1)
        new_datetime_aware = timezone.make_aware(datetime.combine(new_date, new_time))
        
        if new_datetime_aware < minimum_time:
            raise HttpError(400, "For same-day changes, please select a time at least 1 hour in advance")
    
    # Find the new time slot
    try:
        new_time_slot = TimeSlot.objects.get(
            room=reservation.room,
            date=new_date,
            time=new_time
        )
    except TimeSlot.DoesNotExist:
        raise HttpError(404, "Time slot not found for the specified date and time")
    
    # Check if new time slot is available
    if new_time_slot.status != 'active':
        raise HttpError(400, "The selected time slot is not available")
    
    # Use transaction to ensure atomicity
    with transaction.atomic():
        # Get old time slot
        old_time_slot = reservation.time_slot
        
        # Lock both time slots
        old_time_slot = TimeSlot.objects.select_for_update().get(id=old_time_slot.id)
        new_time_slot = TimeSlot.objects.select_for_update().get(id=new_time_slot.id)
        
        # Double-check new slot is still available
        if new_time_slot.status != 'active':
            raise HttpError(400, "The selected time slot is no longer available")
        
        # Free the old time slot
        old_time_slot.status = 'active'
        old_time_slot.save()
        
        # Reserve the new time slot
        new_time_slot.status = 'reserved'
        new_time_slot.save()
        
        # Update the reservation - use update_fields to skip validation
        reservation.time_slot = new_time_slot
        reservation.save(update_fields=['time_slot'])
        
        logger.info(f"Reservation {reservation_id} rescheduled from {old_time_slot.date} {old_time_slot.time} to {new_date} {new_time}")
    
    # Refresh from database to get updated relationships
    reservation.refresh_from_db()
    return reservation


@router.patch("/reservations/{reservation_id}/people/", response=ReservationSchema, auth=jwt_auth)
def update_reservation_people(request, reservation_id: int, payload: ReservationPeopleUpdateSchema):
    """
    Update number of people in a reservation (admin only)
    
    Only allows increasing the number of people, not decreasing.
    Automatically recalculates the total price based on pricing rules.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    old_num_people = reservation.num_people
    new_num_people = payload.num_people
    
    # Validate that we're only increasing, not decreasing
    if new_num_people < old_num_people:
        raise HttpError(400, f"Cannot decrease number of people. Current: {old_num_people}, Requested: {new_num_people}")
    
    # If same number, no change needed
    if new_num_people == old_num_people:
        return reservation
    
    # Update number of people
    reservation.num_people = new_num_people
    
    # Recalculate total price using the model's method
    reservation.total_price = reservation.calculate_total_price()
    
    # Save with update_fields to avoid validation issues
    reservation.save(update_fields=['num_people', 'total_price'])
    
    logger.info(f"Reservation {reservation_id} updated: {old_num_people} -> {new_num_people} people, new total: ${reservation.total_price}")
    
    # Refresh from database
    reservation.refresh_from_db()
    return reservation


@router.patch("/reservations/{reservation_id}/", response=ReservationSchema, auth=jwt_auth)
def update_reservation_status(request, reservation_id: int, payload: ReservationUpdateSchema):
    """
    Update reservation status (admin only)
    
    Allows changing reservation status between: pending, paid, cancelled
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    old_status = reservation.status
    new_status = payload.status
    
    # Validate status transition
    if old_status == new_status:
        raise HttpError(400, f"Reservation is already in '{new_status}' status")
    
    # Handle status-specific logic
    if new_status == 'cancelled' and old_status != 'cancelled':
        # Free up the time slot when cancelling
        if reservation.time_slot:
            reservation.time_slot.status = 'active'
            reservation.time_slot.save()
    elif old_status == 'cancelled' and new_status != 'cancelled':
        # Reserve the time slot again when uncancelling
        if reservation.time_slot:
            if reservation.time_slot.status != 'active':
                raise HttpError(400, "Cannot change status: time slot is no longer available")
            reservation.time_slot.status = 'reserved'
            reservation.time_slot.save()
    
    # Update reservation status
    reservation.status = new_status
    reservation.save(update_fields=['status'])
    
    return reservation


@router.get("/stats/", response=ReservationStatsSchema, auth=jwt_auth)
def get_reservation_stats(request):
    """
    Get basic reservation statistics (admin only)
    
    Returns counts by status, revenue, and time-based metrics
    """
    print("=== STATS ENDPOINT CALLED ===")
    import logging
    logger = logging.getLogger(__name__)
    logger.error("=== STATS ENDPOINT CALLED ===")
    
    try:
        # Get current date and time boundaries
        now = timezone.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Basic counts by status
        total_reservations = Reservation.objects.count()
        pending_count = Reservation.objects.filter(status='pending').count()
        paid_count = Reservation.objects.filter(status='paid').count()
        cancelled_count = Reservation.objects.filter(status='cancelled').count()
        
        # Revenue calculation (only from paid reservations)
        revenue_data = Reservation.objects.filter(status='paid').aggregate(
            total_revenue=Sum('total_price')
        )
        total_revenue = float(revenue_data['total_revenue'] or 0)
        
        # Time-based counts
        today_reservations = Reservation.objects.filter(
            time_slot__date=today
        ).count()
        
        this_week_reservations = Reservation.objects.filter(
            time_slot__date__gte=week_start,
            time_slot__date__lte=today
        ).count()
        
        this_month_reservations = Reservation.objects.filter(
            time_slot__date__gte=month_start,
            time_slot__date__lte=today
        ).count()
        
        return {
            "total_reservations": total_reservations,
            "pending_reservations": pending_count,
            "paid_reservations": paid_count,
            "cancelled_reservations": cancelled_count,
            "total_revenue": total_revenue,
            "today_reservations": today_reservations,
            "this_week_reservations": this_week_reservations,
            "this_month_reservations": this_month_reservations
        }
        
    except Exception as e:
        raise HttpError(500, f"Error retrieving statistics: {str(e)}")