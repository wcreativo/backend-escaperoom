from ninja import Router
from ninja.errors import HttpError
from typing import List
from datetime import datetime, date, time
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Reservation
from .schemas import ReservationCreateSchema, ReservationSchema
from apps.rooms.models import Room, TimeSlot

router = Router()


@router.post("/", response=ReservationSchema)
def create_reservation(request, payload: ReservationCreateSchema):
    """Create a new reservation with complete validation"""
    
    # Validate room exists and is active
    try:
        room = get_object_or_404(Room, id=payload.room_id, is_active=True)
    except Room.DoesNotExist:
        raise HttpError(404, "Room not found or not active")
    
    # Parse and validate date and time
    try:
        reservation_date = datetime.strptime(payload.date, "%Y-%m-%d").date()
        reservation_time = datetime.strptime(payload.time, "%H:%M").time()
    except ValueError:
        raise HttpError(400, "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time")
    
    # Validate that the date is not in the past
    if reservation_date < date.today():
        raise HttpError(400, "Cannot make reservations for past dates")
    
    # Validate number of people
    if payload.num_people < 1:
        raise HttpError(400, "Number of people must be at least 1")
    if payload.num_people > 10:  # Reasonable upper limit
        raise HttpError(400, "Number of people cannot exceed 10")
    
    # Find the specific time slot
    try:
        time_slot = TimeSlot.objects.get(
            room=room,
            date=reservation_date,
            time=reservation_time
        )
    except TimeSlot.DoesNotExist:
        raise HttpError(404, "Time slot not found for the specified room, date, and time")
    
    # Validate time slot availability
    if time_slot.status != 'active':
        raise HttpError(400, "The selected time slot is not available")
    
    # Use database transaction to ensure atomicity
    try:
        with transaction.atomic():
            # Create the reservation
            reservation = Reservation(
                room=room,
                time_slot=time_slot,
                customer_name=payload.customer_name.strip(),
                customer_email=payload.customer_email.strip().lower(),
                customer_phone=payload.customer_phone.strip(),
                num_people=payload.num_people
            )
            
            # The save method will automatically:
            # - Calculate total_price
            # - Set expires_at
            # - Mark time_slot as reserved
            # - Validate the reservation
            reservation.save()
            
            return reservation
            
    except ValidationError as e:
        raise HttpError(400, f"Validation error: {str(e)}")
    except Exception as e:
        raise HttpError(500, f"Error creating reservation: {str(e)}")


