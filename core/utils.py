"""
Utility functions for the escape rooms project.
"""

from datetime import datetime, time
from typing import List, Tuple


def get_business_hours(day_of_week: int) -> Tuple[time, time]:
    """
    Get business hours for a given day of the week.
    
    Args:
        day_of_week: 0=Monday, 1=Tuesday, ..., 6=Sunday
        
    Returns:
        Tuple of (start_time, end_time)
    """
    # Monday to Thursday: 12:00 PM to 9:00 PM
    if 0 <= day_of_week <= 3:
        return time(12, 0), time(21, 0)
    
    # Friday: 12:00 PM to 10:00 PM
    elif day_of_week == 4:
        return time(12, 0), time(22, 0)
    
    # Saturday: 10:00 AM to 10:00 PM
    elif day_of_week == 5:
        return time(10, 0), time(22, 0)
    
    # Sunday: 10:00 AM to 9:00 PM
    elif day_of_week == 6:
        return time(10, 0), time(21, 0)
    
    else:
        raise ValueError("Invalid day of week")


def generate_time_slots(date: datetime.date, room_id: int) -> List[time]:
    """
    Generate available time slots for a given date and room.
    
    Args:
        date: The date to generate slots for
        room_id: The room ID
        
    Returns:
        List of time objects representing available slots
    """
    day_of_week = date.weekday()
    start_time, end_time = get_business_hours(day_of_week)
    
    slots = []
    current_time = start_time
    
    # Generate hourly slots
    while current_time < end_time:
        slots.append(current_time)
        # Add one hour
        hour = current_time.hour + 1
        if hour >= 24:
            break
        current_time = time(hour, current_time.minute)
    
    return slots


def calculate_reservation_price(num_people: int, base_price: float = 30.0) -> float:
    """
    Calculate the total price for a reservation based on number of people.
    
    Args:
        num_people: Number of people in the reservation
        base_price: Base price per person (default: 30.0)
        
    Returns:
        Total price for the reservation
    """
    if num_people <= 3:
        price_per_person = base_price
    else:
        price_per_person = base_price * 0.833  # 25.0 if base_price is 30.0
    
    return num_people * price_per_person