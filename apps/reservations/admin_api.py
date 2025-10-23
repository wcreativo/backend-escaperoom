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


@router.get("/debug/", auth=jwt_auth)
def debug_endpoint(request):
    """Debug endpoint to test what's happening"""
    import logging
    logger = logging.getLogger(__name__)
    
    print("=== DEBUG ENDPOINT CALLED ===")
    print(f"request.GET: {dict(request.GET)}")
    print(f"request.method: {request.method}")
    print(f"request.path: {request.path}")
    
    logger.error("=== DEBUG ENDPOINT CALLED ===")
    logger.error(f"request.GET: {dict(request.GET)}")
    logger.error(f"request.method: {request.method}")
    logger.error(f"request.path: {request.path}")
    
    return {"status": "ok", "params": dict(request.GET)}


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
    
    # Log INMEDIATAMENTE al entrar al endpoint con TODOS los parámetros RAW
    print("=== ADMIN API ENDPOINT CALLED ===")
    print(f"RAW request.GET: {dict(request.GET)}")
    print(f"RAW request.GET items: {list(request.GET.items())}")
    
    logger.error("=== ADMIN API ENDPOINT CALLED ===")
    logger.error(f"RAW request.GET: {dict(request.GET)}")
    logger.error(f"RAW request.GET items: {list(request.GET.items())}")
    
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
    
    # Log parsed parameters
    print(f"PARSED PARAMETERS:")
    print(f"  page: {page} (type: {type(page)})")
    print(f"  per_page: {per_page} (type: {type(per_page)})")
    print(f"  status: {status} (type: {type(status)})")
    print(f"  room_id: {room_id} (type: {type(room_id)})")
    print(f"  search: {search} (type: {type(search)})")
    print(f"  date_from: {date_from} (type: {type(date_from)})")
    print(f"  date_to: {date_to} (type: {type(date_to)})")
    
    logger.error(f"PARSED PARAMETERS:")
    logger.error(f"  page: {page} (type: {type(page)})")
    logger.error(f"  per_page: {per_page} (type: {type(per_page)})")
    logger.error(f"  status: {status} (type: {type(status)})")
    logger.error(f"  room_id: {room_id} (type: {type(room_id)})")
    logger.error(f"  search: {search} (type: {type(search)})")
    logger.error(f"  date_from: {date_from} (type: {type(date_from)})")
    logger.error(f"  date_to: {date_to} (type: {type(date_to)})")
    
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
                logger.info(f"Reservation {i+1} serialized successfully: {reservation.id}")
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