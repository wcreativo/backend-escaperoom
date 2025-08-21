from ninja import Schema
from typing import Optional


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