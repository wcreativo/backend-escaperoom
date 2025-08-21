from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date, timedelta
from ninja.testing import TestClient
from apps.reservations.models import Reservation
from apps.reservations.admin_api import router
from apps.rooms.models import Room, TimeSlot
from apps.authentication.jwt_utils import JWTManager


class AdminReservationAPITestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True
        )
        
        # Create regular user (non-staff)
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            is_staff=False
        )
        
        # Generate JWT tokens
        self.admin_token = JWTManager.generate_access_token(self.admin_user)
        self.regular_token = JWTManager.generate_access_token(self.regular_user)
        
        # Create test client
        self.client = TestClient(router)
        
        # Create test room
        self.room = Room.objects.create(
            name="Test Room",
            slug="test-room",
            short_description="A test room",
            full_description="A detailed test room description",
            base_price=30.00,
            is_active=True
        )
        
        # Create test time slots (both start as active)
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        self.time_slot_1 = TimeSlot.objects.create(
            room=self.room,
            date=today,
            time=datetime.strptime("14:00", "%H:%M").time(),
            status='active'
        )
        
        self.time_slot_2 = TimeSlot.objects.create(
            room=self.room,
            date=tomorrow,
            time=datetime.strptime("16:00", "%H:%M").time(),
            status='active'
        )
        
        # Create test reservations (the save method will automatically mark time slots as reserved)
        self.reservation_1 = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_1,
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="1234567890",
            num_people=2,
            total_price=60.00,
            status='pending',
            expires_at=timezone.now() + timedelta(minutes=30)
        )
        
        self.reservation_2 = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot_2,
            customer_name="Jane Smith",
            customer_email="jane@example.com",
            customer_phone="0987654321",
            num_people=4,
            total_price=100.00,
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=30)
        )

    def test_list_reservations_admin_success(self):
        """Test successful listing of reservations with admin token"""
        response = self.client.get(
            "/reservations/",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("reservations", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("per_page", data)
        self.assertIn("total_pages", data)
        
        # Check data content
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["reservations"]), 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["per_page"], 20)

    def test_list_reservations_unauthorized(self):
        """Test listing reservations without authentication"""
        response = self.client.get("/reservations/")
        self.assertEqual(response.status_code, 401)

    def test_list_reservations_non_staff(self):
        """Test listing reservations with non-staff user"""
        response = self.client.get(
            "/reservations/",
            headers={"Authorization": f"Bearer {self.regular_token}"}
        )
        self.assertEqual(response.status_code, 401)

    def test_list_reservations_with_status_filter(self):
        """Test filtering reservations by status"""
        response = self.client.get(
            "/reservations/?status=paid",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["reservations"][0]["status"], "paid")

    def test_list_reservations_with_search(self):
        """Test searching reservations by customer name"""
        response = self.client.get(
            "/reservations/?search=John",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["reservations"][0]["customer_name"], "John Doe")

    def test_list_reservations_with_room_filter(self):
        """Test filtering reservations by room"""
        response = self.client.get(
            f"/reservations/?room_id={self.room.id}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)

    def test_list_reservations_with_date_filter(self):
        """Test filtering reservations by date range"""
        today_str = date.today().strftime("%Y-%m-%d")
        response = self.client.get(
            f"/reservations/?date_from={today_str}&date_to={today_str}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)

    def test_list_reservations_pagination(self):
        """Test pagination functionality"""
        response = self.client.get(
            "/reservations/?per_page=1&page=1",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["per_page"], 1)
        self.assertEqual(len(data["reservations"]), 1)
        self.assertEqual(data["total_pages"], 2)

    def test_update_reservation_status_success(self):
        """Test successful status update"""
        response = self.client.patch(
            f"/reservations/{self.reservation_1.id}/",
            json={"status": "paid"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "paid")
        
        # Verify database update
        self.reservation_1.refresh_from_db()
        self.assertEqual(self.reservation_1.status, "paid")

    def test_update_reservation_status_to_cancelled(self):
        """Test updating status to cancelled frees up time slot"""
        response = self.client.patch(
            f"/reservations/{self.reservation_1.id}/",
            json={"status": "cancelled"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify time slot is freed
        self.time_slot_1.refresh_from_db()
        self.assertEqual(self.time_slot_1.status, "active")

    def test_update_reservation_status_invalid_status(self):
        """Test updating with invalid status"""
        response = self.client.patch(
            f"/reservations/{self.reservation_1.id}/",
            json={"status": "invalid_status"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_update_reservation_status_same_status(self):
        """Test updating to same status returns error"""
        response = self.client.patch(
            f"/reservations/{self.reservation_1.id}/",
            json={"status": "pending"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 400)

    def test_update_reservation_status_not_found(self):
        """Test updating non-existent reservation"""
        response = self.client.patch(
            "/reservations/99999/",
            json={"status": "paid"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 404)

    def test_update_reservation_status_unauthorized(self):
        """Test updating without authentication"""
        response = self.client.patch(
            f"/reservations/{self.reservation_1.id}/",
            json={"status": "paid"}
        )
        
        self.assertEqual(response.status_code, 401)

    def test_get_stats_success(self):
        """Test successful retrieval of statistics"""
        response = self.client.get(
            "/stats/",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check all required fields are present
        required_fields = [
            "total_reservations", "pending_reservations", "paid_reservations",
            "cancelled_reservations", "total_revenue", "today_reservations",
            "this_week_reservations", "this_month_reservations"
        ]
        
        for field in required_fields:
            self.assertIn(field, data)
        
        # Check values
        self.assertEqual(data["total_reservations"], 2)
        self.assertEqual(data["pending_reservations"], 1)
        self.assertEqual(data["paid_reservations"], 1)
        self.assertEqual(data["cancelled_reservations"], 0)
        self.assertEqual(data["total_revenue"], 100.0)  # Only paid reservations

    def test_get_stats_unauthorized(self):
        """Test getting stats without authentication"""
        response = self.client.get("/stats/")
        self.assertEqual(response.status_code, 401)

    def test_get_stats_non_staff(self):
        """Test getting stats with non-staff user"""
        response = self.client.get(
            "/stats/",
            headers={"Authorization": f"Bearer {self.regular_token}"}
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_filter_values(self):
        """Test various invalid filter values"""
        # Invalid status
        response = self.client.get(
            "/reservations/?status=invalid",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 400)
        
        # Invalid date format
        response = self.client.get(
            "/reservations/?date_from=invalid-date",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 400)
        
        # Page out of range
        response = self.client.get(
            "/reservations/?page=999",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 404)

    def test_uncancelling_reservation_with_unavailable_slot(self):
        """Test uncancelling when time slot is no longer available"""
        # First cancel the reservation
        self.reservation_1.status = 'cancelled'
        self.reservation_1.save(update_fields=['status'])
        
        # Manually set time slot to reserved (simulating another reservation)
        self.time_slot_1.status = 'reserved'
        self.time_slot_1.save()
        
        # Try to uncancel
        response = self.client.patch(
            f"/reservations/{self.reservation_1.id}/",
            json={"status": "paid"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("time slot is no longer available", response.json()["detail"])