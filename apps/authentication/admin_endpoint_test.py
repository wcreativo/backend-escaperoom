from django.test import TestCase, Client
from django.contrib.auth.models import User
import json
from datetime import date, time

from apps.rooms.models import Room, TimeSlot
from apps.reservations.models import Reservation


class AdminEndpointProtectionTest(TestCase):
    """Test that admin endpoints are properly protected with JWT authentication"""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        
        # Create test data
        self.room = Room.objects.create(
            name='Test Room',
            slug='test-room',
            short_description='Test room description',
            full_description='Full test room description',
            base_price=30.00,
            is_active=True
        )
        
        self.time_slot = TimeSlot.objects.create(
            room=self.room,
            date=date(2025, 12, 25),
            time=time(14, 0),
            status='active'
        )
        
        self.reservation = Reservation.objects.create(
            room=self.room,
            time_slot=self.time_slot,
            customer_name='Test Customer',
            customer_email='test@example.com',
            customer_phone='+1234567890',
            num_people=2,
            total_price=60.00,
            status='pending'
        )
        
        # After creating reservation, the time slot should be marked as reserved
        self.time_slot.refresh_from_db()
    
    def test_admin_endpoint_requires_authentication(self):
        """Test that admin endpoints require JWT authentication"""
        
        # Try to access admin endpoint without authentication
        response = self.client.get('/api/reservations/admin/')
        self.assertEqual(response.status_code, 401)
    
    def test_admin_endpoint_with_valid_token(self):
        """Test accessing admin endpoint with valid JWT token"""
        
        # Login to get token
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'admin',
                'password': 'admin123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        access_token = login_data['access_token']
        
        # Access admin endpoint with token
        response = self.client.get(
            '/api/reservations/admin/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify we get the reservation data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['customer_name'], 'Test Customer')
        self.assertEqual(data[0]['room_name'], 'Test Room')
    
    def test_admin_endpoint_with_invalid_token(self):
        """Test accessing admin endpoint with invalid JWT token"""
        
        response = self.client.get(
            '/api/reservations/admin/',
            HTTP_AUTHORIZATION='Bearer invalid.token.here'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_non_staff_user_cannot_access_admin_endpoint(self):
        """Test that non-staff users cannot access admin endpoints even with valid token"""
        
        # Create non-staff user
        regular_user = User.objects.create_user(
            username='regular',
            password='regular123',
            is_staff=False
        )
        
        # Generate token for non-staff user (this would normally fail at login, but testing directly)
        from apps.authentication.jwt_utils import JWTManager
        token = JWTManager.generate_access_token(regular_user)
        
        # Try to access admin endpoint
        response = self.client.get(
            '/api/reservations/admin/',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        # Should be unauthorized because user is not staff
        self.assertEqual(response.status_code, 401)