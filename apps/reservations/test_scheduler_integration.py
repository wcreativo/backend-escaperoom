"""
Integration tests for the APScheduler functionality.
These tests verify the scheduler works in a more realistic environment.
"""

import time
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from apps.reservations.models import Reservation
from apps.rooms.models import Room, TimeSlot
from escape_rooms_backend.scheduler import start_scheduler, stop_scheduler

# Test scheduler configuration using memory job store
TEST_SCHEDULER_CONFIG = {
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


@override_settings(SCHEDULER_CONFIG=TEST_SCHEDULER_CONFIG)
class SchedulerIntegrationTestCase(TransactionTestCase):
    """Integration tests for scheduler functionality"""

    def setUp(self):
        """Set up test data"""
        self.room = Room.objects.create(
            name="Integration Test Room",
            short_description="A test room for integration tests",
            full_description="A detailed test room description for integration tests",
            base_price=30.00
        )
        
        self.time_slot = TimeSlot.objects.create(
            room=self.room,
            date=timezone.now().date(),
            time=timezone.now().time(),
            status='active'
        )

    def test_scheduler_cancels_reservation_automatically(self):
        """
        Test that the scheduler actually cancels expired reservations when running.
        This is a more realistic integration test.
        """
        # Create a reservation that expires very soon (in 2 seconds)
        near_future = timezone.now() + timedelta(seconds=2)
        reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="Integration Test User",
            customer_email="integration@example.com",
            customer_phone="123456789",
            num_people=2,
            total_price=60.00,
            status='pending',
            expires_at=near_future
        )
        
        # Verify initial state
        self.assertEqual(reservation.status, 'pending')
        self.assertEqual(self.time_slot.status, 'reserved')
        
        # Start scheduler in background mode
        scheduler = start_scheduler(blocking=False, config=TEST_SCHEDULER_CONFIG)
        
        try:
            # Wait for the reservation to expire and for the scheduler to process it
            # We need to wait a bit longer than the expiration time plus job interval
            time.sleep(5)
            
            # Refresh from database
            reservation.refresh_from_db()
            self.time_slot.refresh_from_db()
            
            # Verify the reservation was cancelled by the scheduler
            self.assertEqual(reservation.status, 'cancelled')
            self.assertEqual(self.time_slot.status, 'active')
            
        finally:
            # Always clean up the scheduler
            stop_scheduler(scheduler)

    def test_scheduler_handles_multiple_reservations(self):
        """Test that scheduler can handle multiple reservations expiring at different times"""
        # Create additional time slots
        time_slot_2 = TimeSlot.objects.create(
            room=self.room,
            date=timezone.now().date() + timedelta(days=1),
            time=timezone.now().time(),
            status='active'
        )
        
        time_slot_3 = TimeSlot.objects.create(
            room=self.room,
            date=timezone.now().date() + timedelta(days=2),
            time=timezone.now().time(),
            status='active'
        )
        
        # Create reservations with different expiration times
        now = timezone.now()
        
        # This one expires in 2 seconds
        reservation_1 = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="User 1",
            customer_email="user1@example.com",
            customer_phone="111111111",
            num_people=2,
            total_price=60.00,
            status='pending',
            expires_at=now + timedelta(seconds=2)
        )
        
        # This one expires in 4 seconds
        reservation_2 = Reservation.objects.create(
            room=self.room,
            time_slot=time_slot_2,
            customer_name="User 2",
            customer_email="user2@example.com",
            customer_phone="222222222",
            num_people=3,
            total_price=90.00,
            status='pending',
            expires_at=now + timedelta(seconds=4)
        )
        
        # This one doesn't expire for a long time
        reservation_3 = Reservation.objects.create(
            room=self.room,
            time_slot=time_slot_3,
            customer_name="User 3",
            customer_email="user3@example.com",
            customer_phone="333333333",
            num_people=1,
            total_price=30.00,
            status='pending',
            expires_at=now + timedelta(hours=1)
        )
        
        # Start scheduler
        scheduler = start_scheduler(blocking=False, config=TEST_SCHEDULER_CONFIG)
        
        try:
            # Wait for first reservation to expire
            time.sleep(3)
            
            # Check first reservation
            reservation_1.refresh_from_db()
            self.time_slot.refresh_from_db()
            self.assertEqual(reservation_1.status, 'cancelled')
            self.assertEqual(self.time_slot.status, 'active')
            
            # Second and third should still be pending
            reservation_2.refresh_from_db()
            reservation_3.refresh_from_db()
            self.assertEqual(reservation_2.status, 'pending')
            self.assertEqual(reservation_3.status, 'pending')
            
            # Wait for second reservation to expire
            time.sleep(3)
            
            # Check second reservation
            reservation_2.refresh_from_db()
            time_slot_2.refresh_from_db()
            self.assertEqual(reservation_2.status, 'cancelled')
            self.assertEqual(time_slot_2.status, 'active')
            
            # Third should still be pending
            reservation_3.refresh_from_db()
            time_slot_3.refresh_from_db()
            self.assertEqual(reservation_3.status, 'pending')
            self.assertEqual(time_slot_3.status, 'reserved')
            
        finally:
            # Clean up
            stop_scheduler(scheduler)

    def test_scheduler_respects_paid_reservations(self):
        """Test that scheduler doesn't cancel paid reservations even if expired"""
        # Create an expired but paid reservation
        past_time = timezone.now() - timedelta(minutes=1)
        paid_reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="Paid User",
            customer_email="paid@example.com",
            customer_phone="999999999",
            num_people=2,
            total_price=60.00,
            status='paid',  # Already paid
            expires_at=past_time  # Already expired
        )
        
        # Start scheduler
        scheduler = start_scheduler(blocking=False, config=TEST_SCHEDULER_CONFIG)
        
        try:
            # Wait for scheduler to run
            time.sleep(3)
            
            # Verify paid reservation was not cancelled
            paid_reservation.refresh_from_db()
            self.time_slot.refresh_from_db()
            self.assertEqual(paid_reservation.status, 'paid')
            self.assertEqual(self.time_slot.status, 'reserved')
            
        finally:
            # Clean up
            stop_scheduler(scheduler)

    def test_scheduler_startup_and_shutdown(self):
        """Test that scheduler starts and stops cleanly"""
        # Start scheduler
        scheduler = start_scheduler(blocking=False, config=TEST_SCHEDULER_CONFIG)
        
        # Verify it's running
        self.assertTrue(scheduler.running)
        
        # Verify job is scheduled
        jobs = scheduler.get_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].id, 'cancel_expired_reservations')
        
        # Stop scheduler
        stop_scheduler(scheduler)
        
        # Verify it's stopped
        self.assertFalse(scheduler.running)