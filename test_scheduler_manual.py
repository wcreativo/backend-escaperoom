#!/usr/bin/env python
"""
Manual test script to verify scheduler functionality.
Run this with: python manage.py shell < test_scheduler_manual.py
"""

import os
import django
from django.utils import timezone
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'escape_rooms_backend.settings')
django.setup()

from apps.reservations.models import Reservation
from apps.rooms.models import Room, TimeSlot
from escape_rooms_backend.scheduler import cancel_expired_reservations

def test_scheduler_functionality():
    """Test the scheduler functionality manually"""
    print("=== Testing APScheduler Functionality ===")
    
    # Create test data
    room = Room.objects.create(
        name="Manual Test Room",
        short_description="A test room for manual testing",
        full_description="A detailed test room description for manual testing",
        base_price=30.00
    )
    
    time_slot = TimeSlot.objects.create(
        room=room,
        date=timezone.now().date(),
        time=timezone.now().time(),
        status='active'
    )
    
    # Create an expired reservation
    past_time = timezone.now() - timedelta(minutes=35)
    expired_reservation = Reservation.objects.create(
        room=room,
        time_slot=time_slot,
        customer_name="Manual Test User",
        customer_email="manual@example.com",
        customer_phone="123456789",
        num_people=2,
        total_price=60.00,
        status='pending',
        created_at=past_time,
        expires_at=past_time + timedelta(minutes=30)  # Expired 5 minutes ago
    )
    
    print(f"Created expired reservation: {expired_reservation.id}")
    print(f"Initial status: {expired_reservation.status}")
    print(f"Time slot status: {time_slot.status}")
    print(f"Expires at: {expired_reservation.expires_at}")
    print(f"Current time: {timezone.now()}")
    print(f"Is expired: {expired_reservation.is_expired}")
    
    # Run the cancellation function
    print("\n--- Running cancel_expired_reservations() ---")
    cancel_expired_reservations()
    
    # Check results
    expired_reservation.refresh_from_db()
    time_slot.refresh_from_db()
    
    print(f"\nAfter cancellation:")
    print(f"Reservation status: {expired_reservation.status}")
    print(f"Time slot status: {time_slot.status}")
    
    # Verify results
    if expired_reservation.status == 'cancelled' and time_slot.status == 'active':
        print("\n✅ SUCCESS: Scheduler functionality works correctly!")
    else:
        print("\n❌ FAILURE: Scheduler did not work as expected")
    
    # Clean up
    expired_reservation.delete()
    time_slot.delete()
    room.delete()
    print("\n--- Test data cleaned up ---")

if __name__ == "__main__":
    test_scheduler_functionality()