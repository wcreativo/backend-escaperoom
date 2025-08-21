#!/usr/bin/env python
"""
Demonstration script for the APScheduler functionality.
This script shows how the scheduler automatically cancels expired reservations.
"""

import os
import sys
import django
import time
from datetime import timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'escape_rooms_backend.settings')
django.setup()

from django.utils import timezone
from apps.reservations.models import Reservation
from apps.rooms.models import Room, TimeSlot
from escape_rooms_backend.scheduler import start_scheduler, stop_scheduler

def demo_scheduler():
    """Demonstrate the scheduler functionality"""
    print("🚀 APScheduler Demo - Automatic Reservation Cancellation")
    print("=" * 60)
    
    # Create test data
    print("\n📝 Creating test data...")
    room = Room.objects.create(
        name="Demo Escape Room",
        short_description="A demo room",
        full_description="A detailed demo room description",
        base_price=30.00
    )
    
    time_slot = TimeSlot.objects.create(
        room=room,
        date=timezone.now().date(),
        time=timezone.now().time(),
        status='active'
    )
    
    # Create a reservation that will expire in 5 seconds
    expires_in_seconds = 5
    reservation = Reservation.objects.create(
        room=room,
        time_slot=time_slot,
        customer_name="Demo User",
        customer_email="demo@example.com",
        customer_phone="123456789",
        num_people=2,
        total_price=60.00,
        status='pending',
        expires_at=timezone.now() + timedelta(seconds=expires_in_seconds)
    )
    
    print(f"✅ Created reservation {reservation.id}")
    print(f"   Customer: {reservation.customer_name}")
    print(f"   Status: {reservation.status}")
    print(f"   Time Slot Status: {time_slot.status}")
    print(f"   Expires at: {reservation.expires_at}")
    print(f"   Will expire in {expires_in_seconds} seconds...")
    
    # Start scheduler with memory job store for demo
    print(f"\n⚡ Starting scheduler...")
    test_config = {
        'apscheduler.jobstores.default': {
            'type': 'memory'
        },
        'apscheduler.executors.default': {
            'type': 'threadpool',
            'max_workers': 20
        },
        'apscheduler.job_defaults.coalesce': False,
        'apscheduler.job_defaults.max_instances': 3,
        'apscheduler.timezone': 'UTC',
    }
    
    scheduler = start_scheduler(blocking=False, config=test_config)
    print(f"✅ Scheduler started (jobs run every minute)")
    
    try:
        # Wait for reservation to expire and be processed
        print(f"\n⏳ Waiting for reservation to expire and be cancelled...")
        print("   (This may take up to 1 minute for the scheduler job to run)")
        
        # Check status every few seconds
        for i in range(12):  # Check for up to 2 minutes
            time.sleep(10)  # Wait 10 seconds between checks
            
            reservation.refresh_from_db()
            time_slot.refresh_from_db()
            
            print(f"   Check {i+1}: Reservation status = {reservation.status}, "
                  f"Time slot status = {time_slot.status}")
            
            if reservation.status == 'cancelled':
                print(f"\n🎉 SUCCESS! Reservation was automatically cancelled!")
                print(f"   Reservation status: {reservation.status}")
                print(f"   Time slot status: {time_slot.status}")
                break
        else:
            print(f"\n⚠️  Reservation not cancelled yet. This is normal as jobs run every minute.")
            print(f"   Current status: {reservation.status}")
            print(f"   Is expired: {reservation.is_expired}")
    
    finally:
        # Clean up
        print(f"\n🧹 Cleaning up...")
        stop_scheduler(scheduler)
        reservation.delete()
        time_slot.delete()
        room.delete()
        print(f"✅ Demo completed and cleaned up!")

if __name__ == "__main__":
    demo_scheduler()