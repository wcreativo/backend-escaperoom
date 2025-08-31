from ninja import Router, Query
from ninja.errors import HttpError
from typing import List
from datetime import date, datetime
from django.shortcuts import get_object_or_404
from .models import Room, TimeSlot
from .schemas import RoomSchema, AvailabilityResponseSchema, TimeSlotSchema

router = Router()


@router.get("/", response=List[RoomSchema])
def list_rooms(request):
    """List all active rooms"""
    return Room.objects.filter(is_active=True)


@router.get("/{room_id}/", response=RoomSchema)
def get_room(request, room_id: int):
    """Get room details by ID"""
    try:
        return get_object_or_404(Room, id=room_id, is_active=True)
    except Room.DoesNotExist:
        raise HttpError(404, "Room not found")


@router.get("/{room_id}/availability/", response=AvailabilityResponseSchema)
def get_room_availability(request, room_id: int, date_param: date = Query(None, alias="date")):
    """Get available time slots for a specific room on a given date"""
    try:
        room = get_object_or_404(Room, id=room_id, is_active=True)
    except Room.DoesNotExist:
        raise HttpError(404, "Room not found")
    
    # Use provided date or default to today
    target_date = date_param if date_param else date.today()
    
    # Get available time slots for the room on the specified date
    available_slots = TimeSlot.objects.filter(
        room=room,
        date=target_date,
        status='active'
    ).order_by('time')
    
    return AvailabilityResponseSchema(
        room_id=room.id,
        room_name=room.name,
        date=target_date,
        available_times=[
            TimeSlotSchema(
                id=slot.id,
                date=slot.date,
                time=slot.time,
                status=slot.status
            ) for slot in available_slots
        ]
    )


@router.get("/{room_id}/all-slots/", response=AvailabilityResponseSchema)
def get_room_all_slots(request, room_id: int, date_param: date = Query(None, alias="date")):
    """Get all time slots (available and reserved) for a specific room on a given date"""
    try:
        room = get_object_or_404(Room, id=room_id, is_active=True)
    except Room.DoesNotExist:
        raise HttpError(404, "Room not found")
    
    # Use provided date or default to today
    target_date = date_param if date_param else date.today()
    
    # Get ALL time slots for the room on the specified date (both active and reserved)
    all_slots = TimeSlot.objects.filter(
        room=room,
        date=target_date
    ).order_by('time')
    
    return AvailabilityResponseSchema(
        room_id=room.id,
        room_name=room.name,
        date=target_date,
        available_times=[
            TimeSlotSchema(
                id=slot.id,
                date=slot.date,
                time=slot.time,
                status=slot.status
            ) for slot in all_slots
        ]
    )