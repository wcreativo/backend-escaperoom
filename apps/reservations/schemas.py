from ninja import Schema
from datetime import datetime
from typing import Optional


class ReservationCreateSchema(Schema):
    room_id: int
    date: str
    time: str
    customer_name: str
    customer_email: str
    customer_phone: str
    num_people: int


class ReservationSchema(Schema):
    id: int
    room_id: int
    customer_name: str
    customer_email: str
    customer_phone: str
    num_people: int
    total_price: float
    status: str
    created_at: datetime
    expires_at: datetime