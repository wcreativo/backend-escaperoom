from ninja import Schema
from datetime import datetime
from typing import Optional, List
from pydantic import validator
import re


class ReservationCreateSchema(Schema):
    room_id: int
    date: str  # Format: YYYY-MM-DD
    time: str  # Format: HH:MM
    customer_name: str
    customer_email: str
    customer_phone: str
    num_people: int
    
    @validator('customer_name')
    def validate_customer_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Customer name is required')
        if len(v.strip()) < 2:
            raise ValueError('Customer name must be at least 2 characters long')
        if len(v.strip()) > 100:
            raise ValueError('Customer name cannot exceed 100 characters')
        return v.strip()
    
    @validator('customer_email')
    def validate_customer_email(cls, v):
        if not v or not v.strip():
            raise ValueError('Customer email is required')
        
        # Simple email validation regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.strip()):
            raise ValueError('Invalid email format')
        
        return v.strip().lower()
    
    @validator('customer_phone')
    def validate_customer_phone(cls, v):
        if not v or not v.strip():
            raise ValueError('Customer phone is required')
        # Remove common phone formatting characters
        cleaned_phone = ''.join(filter(str.isdigit, v))
        if len(cleaned_phone) < 8:
            raise ValueError('Phone number must have at least 8 digits')
        if len(cleaned_phone) > 15:
            raise ValueError('Phone number cannot exceed 15 digits')
        return v.strip()
    
    @validator('num_people')
    def validate_num_people(cls, v):
        if v < 1:
            raise ValueError('Number of people must be at least 1')
        if v > 10:
            raise ValueError('Number of people cannot exceed 10')
        return v


class ReservationSchema(Schema):
    id: int
    room_id: int
    room_name: str
    customer_name: str
    customer_email: str
    customer_phone: str
    date: str
    time: str
    num_people: int
    total_price: float
    status: str
    created_at: datetime
    expires_at: datetime
    
    @staticmethod
    def resolve_room_id(obj):
        return obj.room.id
    
    @staticmethod
    def resolve_room_name(obj):
        return obj.room.name
    
    @staticmethod
    def resolve_date(obj):
        return obj.time_slot.date.strftime('%Y-%m-%d') if obj.time_slot else None
    
    @staticmethod
    def resolve_time(obj):
        return obj.time_slot.time.strftime('%H:%M:%S') if obj.time_slot else None


class ReservationUpdateSchema(Schema):
    status: str
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['pending', 'paid', 'cancelled']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class ReservationListSchema(Schema):
    reservations: List[ReservationSchema]
    total: int
    page: int
    per_page: int
    total_pages: int


class ReservationStatsSchema(Schema):
    total_reservations: int
    pending_reservations: int
    paid_reservations: int
    cancelled_reservations: int
    total_revenue: float
    today_reservations: int
    this_week_reservations: int
    this_month_reservations: int