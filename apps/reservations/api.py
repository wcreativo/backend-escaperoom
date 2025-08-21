from ninja import Router
from typing import List
from .models import Reservation
from .schemas import ReservationCreateSchema, ReservationSchema

router = Router()


@router.post("/", response=ReservationSchema)
def create_reservation(request, payload: ReservationCreateSchema):
    """Create a new reservation"""
    # This will be implemented in later tasks
    pass


@router.get("/", response=List[ReservationSchema])
def list_reservations(request):
    """List all reservations (admin only)"""
    # This will be implemented in later tasks with authentication
    pass