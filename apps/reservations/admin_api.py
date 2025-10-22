from ninja import Router, Query
from ninja.errors import HttpError
from typing import Optional
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from .models import Reservation
from .schemas import (
    ReservationSchema, 
    ReservationUpdateSchema,
    ReservationListSchema,
    ReservationStatsSchema
)
from apps.authentication.middleware import jwt_auth

router = Router()


@router.get("/reservations/", response=ReservationListSchema, auth=jwt_auth)
def list_reservations_admin(
    request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    room_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
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
    
    # Log INMEDIATAMENTE al entrar al endpoint
    print("=== ADMIN API ENDPOINT CALLED ===")
    logger.error("=== ADMIN API ENDPOINT CALLED ===")
    
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
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')
    
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
                # Test serialization of individual reservation
                reservation_data = {
                    "id": reservation.id,
                    "room_id": reservation.room.id if reservation.room else None,
                    "room_name": reservation.room.name if reservation.room else None,
                    "customer_name": reservation.customer_name,
                    "customer_email": reservation.customer_email,
                    "customer_phone": reservation.customer_phone,
                    "date": reservation.time_slot.date.strftime('%Y-%m-%d') if reservation.time_slot else None,
                    "time": reservation.time_slot.time.strftime('%H:%M:%S') if reservation.time_slot else None,
                    "num_people": reservation.num_people,
                    "total_price": float(reservation.total_price),
                    "status": reservation.status,
                    "created_at": reservation.created_at,
                    "expires_at": reservation.expires_at
                }
                reservations_list.append(reservation_data)
                logger.info(f"Reservation {i+1} serialized successfully: {reservation.id}")
            except Exception as e:
                logger.error(f"Error serializing reservation {reservation.id}: {str(e)}")
                logger.error(f"Reservation data: room={reservation.room}, time_slot={reservation.time_slot}")
                raise HttpError(500, f"Data serialization error for reservation {reservation.id}: {str(e)}")
        
        response_data = {
            "reservations": reservations_list,
            "total": paginator.count,
            "page": page,
            "per_page": per_page,
            "total_pages": paginator.num_pages
        }
        
        logger.info(f"Response prepared successfully with {len(reservations_list)} reservations")
        return response_data
        
    except Exception as e:
        logger.error(f"Error in pagination/serialization: {str(e)}")
        raise HttpError(500, f"Error processing reservations: {str(e)}")


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