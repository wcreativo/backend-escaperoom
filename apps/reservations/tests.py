from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date, time, timedelta
from decimal import Decimal
from ninja.testing import TestClient
from apps.rooms.models import Room, TimeSlot
from apps.reservations.models import Reservation
from apps.reservations.api import router


class ReservationModelTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.room = Room.objects.create(
            name="Test Escape Room",
            short_description="A test room",
            full_description="A detailed test room description",
            base_price=Decimal('30.00')
        )
        
        self.time_slot = TimeSlot.objects.create(
            room=self.room,
            date=date.today() + timedelta(days=1),
            time=time(14, 0),  # 2:00 PM
            status='active'
        )

    def test_calculate_total_price_1_to_3_people(self):
        """Test price calculation for 1-3 people ($30 each)"""
        # Test 1 person
        reservation = Reservation(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=1
        )
        self.assertEqual(reservation.calculate_total_price(), Decimal('30.00'))
        
        # Test 2 people
        reservation.num_people = 2
        self.assertEqual(reservation.calculate_total_price(), Decimal('60.00'))
        
        # Test 3 people
        reservation.num_people = 3
        self.assertEqual(reservation.calculate_total_price(), Decimal('90.00'))

    def test_calculate_total_price_4_or_more_people(self):
        """Test price calculation for 4+ people ($25 each)"""
        reservation = Reservation(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=4
        )
        self.assertEqual(reservation.calculate_total_price(), Decimal('100.00'))
        
        # Test 5 people
        reservation.num_people = 5
        self.assertEqual(reservation.calculate_total_price(), Decimal('125.00'))
        
        # Test 10 people
        reservation.num_people = 10
        self.assertEqual(reservation.calculate_total_price(), Decimal('250.00'))

    def test_reservation_save_auto_calculates_price(self):
        """Test that saving a reservation automatically calculates the total price"""
        reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=4
        )
        self.assertEqual(reservation.total_price, Decimal('100.00'))

    def test_reservation_save_marks_timeslot_reserved(self):
        """Test that saving a reservation marks the time slot as reserved"""
        self.assertEqual(self.time_slot.status, 'active')
        
        Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=2
        )
        
        # Refresh from database
        self.time_slot.refresh_from_db()
        self.assertEqual(self.time_slot.status, 'reserved')

    def test_reservation_save_sets_expires_at(self):
        """Test that saving a reservation sets expires_at to 30 minutes from creation"""
        before_creation = timezone.now()
        reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=2
        )
        after_creation = timezone.now()
        
        expected_expiry_min = before_creation + timedelta(minutes=30)
        expected_expiry_max = after_creation + timedelta(minutes=30)
        
        self.assertGreaterEqual(reservation.expires_at, expected_expiry_min)
        self.assertLessEqual(reservation.expires_at, expected_expiry_max)

    def test_reservation_validation_unavailable_timeslot(self):
        """Test that creating a reservation with unavailable time slot fails"""
        # Mark time slot as reserved
        self.time_slot.status = 'reserved'
        self.time_slot.save()
        
        with self.assertRaises(ValidationError):
            reservation = Reservation(
                room=self.room,
                time_slot=self.time_slot,
                customer_name="John Doe",
                customer_email="john@example.com",
                customer_phone="1234567890",
                num_people=2
            )
            reservation.full_clean()

    def test_reservation_validation_mismatched_room_timeslot(self):
        """Test that creating a reservation with mismatched room and time slot fails"""
        # Create another room
        other_room = Room.objects.create(
            name="Other Room",
            short_description="Another room",
            full_description="Another room description",
            base_price=Decimal('30.00')
        )
        
        with self.assertRaises(ValidationError):
            reservation = Reservation(
                room=other_room,  # Different room
                time_slot=self.time_slot,  # Time slot belongs to self.room
                customer_name="John Doe",
                customer_email="john@example.com",
                customer_phone="1234567890",
                num_people=2
            )
            reservation.full_clean()

    def test_cancel_reservation(self):
        """Test canceling a reservation frees up the time slot"""
        reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=2
        )
        
        # Verify time slot is reserved
        self.time_slot.refresh_from_db()
        self.assertEqual(self.time_slot.status, 'reserved')
        
        # Cancel reservation
        reservation.cancel_reservation()
        
        # Verify reservation is cancelled and time slot is active
        self.assertEqual(reservation.status, 'cancelled')
        self.time_slot.refresh_from_db()
        self.assertEqual(self.time_slot.status, 'active')

    def test_is_expired_property(self):
        """Test the is_expired property"""
        # Create reservation with past expiry
        past_time = timezone.now() - timedelta(minutes=1)
        reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=2
        )
        
        # Manually update expires_at using update to avoid validation
        Reservation.objects.filter(id=reservation.id).update(expires_at=past_time)
        reservation.refresh_from_db()
        
        self.assertTrue(reservation.is_expired)
        
        # Test paid reservation is not considered expired
        reservation.status = 'paid'
        reservation.save(update_fields=['status'])
        self.assertFalse(reservation.is_expired)


class ReservationAPITest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = TestClient(router)
        
        self.room = Room.objects.create(
            name="Test Escape Room",
            short_description="A test room",
            full_description="A detailed test room description",
            base_price=Decimal('30.00'),
            is_active=True
        )
        
        self.time_slot = TimeSlot.objects.create(
            room=self.room,
            date=date.today() + timedelta(days=1),
            time=time(14, 0),  # 2:00 PM
            status='active'
        )
        
        self.valid_payload = {
            "room_id": self.room.id,
            "date": str(date.today() + timedelta(days=1)),
            "time": "14:00",
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "customer_phone": "1234567890",
            "num_people": 2
        }

    def test_create_reservation_success(self):
        """Test successful reservation creation"""
        response = self.client.post("/", json=self.valid_payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["room_id"], self.room.id)
        self.assertEqual(data["room_name"], self.room.name)
        self.assertEqual(data["customer_name"], "John Doe")
        self.assertEqual(data["customer_email"], "john@example.com")
        self.assertEqual(data["num_people"], 2)
        self.assertEqual(data["total_price"], 60.0)  # 2 people * $30
        self.assertEqual(data["status"], "pending")
        
        # Verify time slot is marked as reserved
        self.time_slot.refresh_from_db()
        self.assertEqual(self.time_slot.status, 'reserved')

    def test_create_reservation_invalid_room(self):
        """Test reservation creation with invalid room ID"""
        payload = self.valid_payload.copy()
        payload["room_id"] = 99999
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 404)

    def test_create_reservation_inactive_room(self):
        """Test reservation creation with inactive room"""
        self.room.is_active = False
        self.room.save()
        
        response = self.client.post("/", json=self.valid_payload)
        self.assertEqual(response.status_code, 404)

    def test_create_reservation_invalid_date_format(self):
        """Test reservation creation with invalid date format"""
        payload = self.valid_payload.copy()
        payload["date"] = "invalid-date"
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_create_reservation_invalid_time_format(self):
        """Test reservation creation with invalid time format"""
        payload = self.valid_payload.copy()
        payload["time"] = "invalid-time"
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_create_reservation_past_date(self):
        """Test reservation creation with past date"""
        payload = self.valid_payload.copy()
        payload["date"] = str(date.today() - timedelta(days=1))
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_create_reservation_invalid_num_people(self):
        """Test reservation creation with invalid number of people"""
        # Test 0 people
        payload = self.valid_payload.copy()
        payload["num_people"] = 0
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 422)  # Pydantic validation error
        
        # Test too many people
        payload["num_people"] = 15
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    def test_create_reservation_nonexistent_timeslot(self):
        """Test reservation creation with non-existent time slot"""
        payload = self.valid_payload.copy()
        payload["time"] = "15:00"  # Time slot doesn't exist
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 404)

    def test_create_reservation_unavailable_timeslot(self):
        """Test reservation creation with unavailable time slot"""
        # Mark time slot as reserved
        self.time_slot.status = 'reserved'
        self.time_slot.save()
        
        response = self.client.post("/", json=self.valid_payload)
        self.assertEqual(response.status_code, 400)

    def test_create_reservation_pricing_tiers(self):
        """Test reservation creation with different pricing tiers"""
        # Test 3 people (should be $30 each = $90)
        payload = self.valid_payload.copy()
        payload["num_people"] = 3
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_price"], 90.0)
        
        # Create another time slot for second test
        time_slot_2 = TimeSlot.objects.create(
            room=self.room,
            date=date.today() + timedelta(days=1),
            time=time(15, 0),
            status='active'
        )
        
        # Test 4 people (should be $25 each = $100)
        payload["time"] = "15:00"
        payload["num_people"] = 4
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_price"], 100.0)

    def test_create_reservation_validation_errors(self):
        """Test reservation creation with various validation errors"""
        # Test empty customer name
        payload = self.valid_payload.copy()
        payload["customer_name"] = ""
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 422)
        
        # Test invalid email
        payload = self.valid_payload.copy()
        payload["customer_email"] = "invalid-email"
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 422)
        
        # Test empty phone
        payload = self.valid_payload.copy()
        payload["customer_phone"] = ""
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_concurrent_reservation_creation(self):
        """Test that concurrent reservations for the same time slot are handled properly"""
        # This test simulates race condition where two requests try to book the same slot
        
        # First reservation should succeed
        response1 = self.client.post("/", json=self.valid_payload)
        self.assertEqual(response1.status_code, 200)
        
        # Second reservation for same slot should fail
        payload2 = self.valid_payload.copy()
        payload2["customer_name"] = "Jane Doe"
        payload2["customer_email"] = "jane@example.com"
        
        response2 = self.client.post("/", json=payload2)
        self.assertEqual(response2.status_code, 400)  # Time slot not available
