from ninja import Router
from typing import List
from .models import Room
from .schemas import RoomSchema

router = Router()


@router.get("/", response=List[RoomSchema])
def list_rooms(request):
    """List all active rooms"""
    return Room.objects.filter(is_active=True)


@router.get("/{room_id}/", response=RoomSchema)
def get_room(request, room_id: int):
    """Get room details by ID"""
    return Room.objects.get(id=room_id, is_active=True)