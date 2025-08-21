from ninja import Schema
from typing import Optional, List
from datetime import date, time


class RoomSchema(Schema):
    id: int
    name: str
    slug: str
    short_description: str
    full_description: str
    hero_image: Optional[str] = None
    thumbnail_image: Optional[str] = None
    base_price: float
    is_active: bool


class TimeSlotSchema(Schema):
    id: int
    date: date
    time: time
    status: str


class AvailabilityResponseSchema(Schema):
    room_id: int
    room_name: str
    date: date
    available_times: List[TimeSlotSchema]