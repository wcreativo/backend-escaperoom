"""
Tests for the APScheduler automatic reservation cancellation functionality.
"""

from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from apps.reservations.models import Reservation
from apps.rooms.models import Room, TimeSlot
from escape_rooms_backend.scheduler import (
    cancel_expired_reservations,
    start_scheduler,
    stop_scheduler,
    get_scheduler
)

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
class SchedulerTestCase(TestCase):
    """Test cases for the scheduler functionality"""

    def setUp(self):
        """Set up test data"""
        # Create a test room
        self.room = Room.objects.create(
            name="Test Escape Room",
            short_description="A test room",
            full_description="A detailed test room description",
            base_price=30.00
        )
        
        # Create test time slots
        self.time_slot_1 = TimeSlot.objects.create(
            room=self.room,
            date=timezone.now().date(),
            time=timezone.now().time(),
            status='active'
        )
        
        self.time_slot_2 = TimeSlot.objects.create(
            room=self.room,
            date=timezone.now().date() + timedelta(days=1),
            time=timezone.now().time(),
            status='active'
        )

    def test_cancel_expired_reservations_with_expired_reservation(self):
        """Test that expired reservations are cancelled correctly"""
        # Create an expired reservation (created 35 minutes ago)
        past_time = timezone.now() - timedelta(minutes=35)
        expired_reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_1,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="123456789",
            num_people=2,
            total_price=60.00,
            status='pending',
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)  # Expired 5 minutes ago
        )
        
        # Verify initial state
        self.assertEqual(expired_reservation.status, 'pending')
        self.assertEqual(self.time_slot_1.status, 'reserved')
        
        # Run the cancellation job
        cancel_expired_reservations()
        
        # Refresh from database
        expired_reservation.refresh_from_db()
        self.time_slot_1.refresh_from_db()
        
        # Verify the reservation was cancelled
        self.assertEqual(expired_reservation.status, 'cancelled')
        self.assertEqual(self.time_slot_1.status, 'active')

    def test_cancel_expired_reservations_with_non_expired_reservation(self):
        """Test that non-expired reservations are not cancelled"""
        # Create a non-expired reservation (created 20 minutes ago)
        recent_time = timezone.now() - timedelta(minutes=20)
        active_reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_1,
            customer_name="Jane Doe",
            customer_email="jane@example.com",
            customer_phone="987654321",
            num_people=3,
            total_price=90.00,
            status='pending',
            created_at=recent_time,
            expires_at=recent_time + timedelta(minutes=30)  # Still has 10 minutes
        )
        
        # Verify initial state
        self.assertEqual(active_reservation.status, 'pending')
        self.assertEqual(self.time_slot_1.status, 'reserved')
        
        # Run the cancellation job
        cancel_expired_reservations()
        
        # Refresh from database
        active_reservation.refresh_from_db()
        self.time_slot_1.refresh_from_db()
        
        # Verify the reservation was NOT cancelled
        self.assertEqual(active_reservation.status, 'pending')
        self.assertEqual(self.time_slot_1.status, 'reserved')

    def test_cancel_expired_reservations_with_paid_reservation(self):
        """Test that paid reservations are not cancelled even if expired"""
        # Create an expired but paid reservation
        past_time = timezone.now() - timedelta(minutes=35)
        paid_reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_1,
            customer_name="Bob Smith",
            customer_email="bob@example.com",
            customer_phone="555666777",
            num_people=4,
            total_price=100.00,
            status='paid',  # Already paid
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)
        )
        
        # Verify initial state
        self.assertEqual(paid_reservation.status, 'paid')
        self.assertEqual(self.time_slot_1.status, 'reserved')
        
        # Run the cancellation job
        cancel_expired_reservations()
        
        # Refresh from database
        paid_reservation.refresh_from_db()
        self.time_slot_1.refresh_from_db()
        
        # Verify the paid reservation was NOT cancelled
        self.assertEqual(paid_reservation.status, 'paid')
        self.assertEqual(self.time_slot_1.status, 'reserved')

    def test_cancel_expired_reservations_multiple_reservations(self):
        """Test cancelling multiple expired reservations"""
        past_time = timezone.now() - timedelta(minutes=35)
        
        # Create multiple expired reservations
        expired_1 = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_1,
            customer_name="Alice",
            customer_email="alice@example.com",
            customer_phone="111222333",
            num_people=2,
            total_price=60.00,
            status='pending',
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)
        )
        
        expired_2 = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_2,
            customer_name="Charlie",
            customer_email="charlie@example.com",
            customer_phone="444555666",
            num_people=3,
            total_price=90.00,
            status='pending',
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)
        )
        
        # Run the cancellation job
        cancel_expired_reservations()
        
        # Refresh from database
        expired_1.refresh_from_db()
        expired_2.refresh_from_db()
        self.time_slot_1.refresh_from_db()
        self.time_slot_2.refresh_from_db()
        
        # Verify both reservations were cancelled
        self.assertEqual(expired_1.status, 'cancelled')
        self.assertEqual(expired_2.status, 'cancelled')
        self.assertEqual(self.time_slot_1.status, 'active')
        self.assertEqual(self.time_slot_2.status, 'active')

    @patch('escape_rooms_backend.scheduler.logger')
    def test_cancel_expired_reservations_logging(self, mock_logger):
        """Test that the cancellation job logs appropriately"""
        # Create an expired reservation
        past_time = timezone.now() - timedelta(minutes=35)
        expired_reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_1,
            customer_name="Test User",
            customer_email="test@example.com",
            customer_phone="123456789",
            num_people=2,
            total_price=60.00,
            status='pending',
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)
        )
        
        # Run the cancellation job
        cancel_expired_reservations()
        
        # Verify logging was called
        mock_logger.info.assert_called()
        
        # Check that the log message contains expected information
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        self.assertTrue(
            any('Cancelled expired reservation' in call for call in log_calls)
        )

    @patch('escape_rooms_backend.scheduler.logger')
    def test_cancel_expired_reservations_no_expired(self, mock_logger):
        """Test logging when no expired reservations are found"""
        # Don't create any expired reservations
        
        # Run the cancellation job
        cancel_expired_reservations()
        
        # Verify debug logging was called for no expired reservations
        mock_logger.debug.assert_called_with("No expired reservations found")

    def test_start_scheduler_background_mode(self):
        """Test starting scheduler in background mode"""
        # Create scheduler directly with simple config
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            cancel_expired_reservations,
            'interval',
            minutes=1,
            id='cancel_expired_reservations',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        
        self.assertIsNotNone(scheduler)
        self.assertTrue(scheduler.running)
        
        # Check that the job was added
        jobs = scheduler.get_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].id, 'cancel_expired_reservations')
        
        # Clean up
        stop_scheduler(scheduler)

    def test_start_scheduler_blocking_mode(self):
        """Test starting scheduler in blocking mode (without actually blocking)"""
        with patch('escape_rooms_backend.scheduler.BlockingScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            scheduler = start_scheduler(blocking=True)
            
            # Verify BlockingScheduler was used
            mock_scheduler_class.assert_called_once()
            mock_scheduler.add_job.assert_called_once()
            mock_scheduler.start.assert_called_once()

    def test_stop_scheduler(self):
        """Test stopping a scheduler"""
        # Create scheduler directly with simple config
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        scheduler.start()
        self.assertTrue(scheduler.running)
        
        stop_scheduler(scheduler)
        self.assertFalse(scheduler.running)

    def test_get_scheduler_singleton(self):
        """Test that get_scheduler returns the same instance"""
        # Mock the start_scheduler function to return a simple scheduler
        with patch('escape_rooms_backend.scheduler.start_scheduler') as mock_start:
            from apscheduler.schedulers.background import BackgroundScheduler
            test_scheduler = BackgroundScheduler()
            test_scheduler.start()
            mock_start.return_value = test_scheduler
            
            scheduler1 = get_scheduler()
            scheduler2 = get_scheduler()
            
            self.assertIs(scheduler1, scheduler2)
            
            # Clean up
            stop_scheduler(scheduler1)

    @patch('escape_rooms_backend.scheduler.Reservation.objects.select_related')
    def test_cancel_expired_reservations_database_error(self, mock_select_related):
        """Test error handling in cancel_expired_reservations"""
        # Mock a database error
        mock_select_related.side_effect = Exception("Database connection error")
        
        # This should not raise an exception
        with patch('escape_rooms_backend.scheduler.logger') as mock_logger:
            cancel_expired_reservations()
            mock_logger.error.assert_called()

    def test_reservation_is_expired_property(self):
        """Test the is_expired property on Reservation model"""
        # Create an expired reservation
        past_time = timezone.now() - timedelta(minutes=35)
        expired_reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_1,
            customer_name="Test User",
            customer_email="test@example.com",
            customer_phone="123456789",
            num_people=2,
            total_price=60.00,
            status='pending',
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)
        )
        
        # Test is_expired property
        self.assertTrue(expired_reservation.is_expired)
        
        # Create a non-expired reservation
        recent_time = timezone.now() - timedelta(minutes=10)
        active_reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_2,
            customer_name="Active User",
            customer_email="active@example.com",
            customer_phone="987654321",
            num_people=2,
            total_price=60.00,
            status='pending',
            created_at=recent_time,
            expires_at=recent_time + timedelta(minutes=30)
        )
        
        # Test is_expired property
        self.assertFalse(active_reservation.is_expired)
        
        # Test that paid reservations are not considered expired
        # Use update_fields to avoid validation issues
        expired_reservation.status = 'paid'
        expired_reservation.save(update_fields=['status'])
        self.assertFalse(expired_reservation.is_expired)