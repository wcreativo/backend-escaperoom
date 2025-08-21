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
    
    @staticmethod
    def resolve_hero_image(obj):
        if obj.hero_image:
            # If it's already a URL, return as is
            if obj.hero_image.name.startswith('http') or obj.hero_image.name.startswith('/'):
                return obj.hero_image.name
            # Otherwise, construct the full URL
            return f"/media/{obj.hero_image.name}" if obj.hero_image.name else None
        return None
    
    @staticmethod
    def resolve_thumbnail_image(obj):
        if obj.thumbnail_image:
            # If it's already a URL, return as is
            if obj.thumbnail_image.name.startswith('http') or obj.thumbnail_image.name.startswith('/'):
                return obj.thumbnail_image.name
            # Otherwise, construct the full URL
            return f"/media/{obj.thumbnail_image.name}" if obj.thumbnail_image.name else None
        return None


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