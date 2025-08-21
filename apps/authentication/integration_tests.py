from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from apps.rooms.models import Room, TimeSlot
from apps.reservations.models import Reservation
from .jwt_utils import JWTManager


class AuthenticationIntegrationTest(TestCase):
    """Integration tests for JWT authentication with protected endpoints"""
    
    def setUp(self):
        self.client = Client()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staff123',
            email='staff@test.com',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            password='user123',
            email='user@test.com',
            is_staff=False
        )
        
        # Create test room and time slot
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
            date='2025-12-25',
            time='14:00:00',
            status='active'
        )
    
    def test_full_authentication_flow(self):
        """Test complete authentication flow from login to protected endpoint access"""
        
        # Step 1: Login with admin credentials
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
        
        # Verify login response structure
        self.assertIn('access_token', login_data)
        self.assertIn('refresh_token', login_data)
        self.assertEqual(login_data['token_type'], 'Bearer')
        self.assertEqual(login_data['expires_in'], 900)
        
        access_token = login_data['access_token']
        refresh_token = login_data['refresh_token']
        
        # Step 2: Access user info endpoint
        user_info_response = self.client.get(
            '/api/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        self.assertEqual(user_info_response.status_code, 200)
        user_data = user_info_response.json()
        
        self.assertEqual(user_data['username'], 'admin')
        self.assertTrue(user_data['is_staff'])
        self.assertTrue(user_data['is_superuser'])
        
        # Step 3: Test token refresh
        refresh_response = self.client.post(
            '/api/auth/refresh',
            data=json.dumps({
                'refresh_token': refresh_token
            }),
            content_type='application/json'
        )
        
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        
        self.assertIn('access_token', refresh_data)
        self.assertEqual(refresh_data['token_type'], 'Bearer')
        
        new_access_token = refresh_data['access_token']
        
        # Step 4: Use new access token
        user_info_response_2 = self.client.get(
            '/api/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {new_access_token}'
        )
        
        self.assertEqual(user_info_response_2.status_code, 200)
        
        # Step 5: Logout
        logout_response = self.client.post(
            '/api/auth/logout',
            HTTP_AUTHORIZATION=f'Bearer {new_access_token}'
        )
        
        self.assertEqual(logout_response.status_code, 200)
        
        # Step 6: Verify token is invalidated (refresh should fail)
        refresh_response_2 = self.client.post(
            '/api/auth/refresh',
            data=json.dumps({
                'refresh_token': refresh_token
            }),
            content_type='application/json'
        )
        
        self.assertEqual(refresh_response_2.status_code, 401)
    
    def test_staff_user_authentication(self):
        """Test that staff users (non-superuser) can also authenticate"""
        
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'staff',
                'password': 'staff123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        
        access_token = login_data['access_token']
        
        # Verify staff user can access protected endpoints
        user_info_response = self.client.get(
            '/api/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        self.assertEqual(user_info_response.status_code, 200)
        user_data = user_info_response.json()
        
        self.assertEqual(user_data['username'], 'staff')
        self.assertTrue(user_data['is_staff'])
        self.assertFalse(user_data['is_superuser'])
    
    def test_regular_user_cannot_authenticate(self):
        """Test that regular users cannot authenticate for admin access"""
        
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'user',
                'password': 'user123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(login_response.status_code, 401)
        error_data = login_response.json()
        self.assertEqual(error_data['error'], 'insufficient_permissions')
    
    def test_invalid_credentials(self):
        """Test authentication with invalid credentials"""
        
        # Wrong password
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'admin',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(login_response.status_code, 401)
        error_data = login_response.json()
        self.assertEqual(error_data['error'], 'invalid_credentials')
        
        # Non-existent user
        login_response_2 = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'nonexistent',
                'password': 'password'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(login_response_2.status_code, 401)
    
    def test_access_without_authentication(self):
        """Test accessing protected endpoints without authentication"""
        
        # Try to access user info without token
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 401)
        
        # Try to logout without token
        response = self.client.post('/api/auth/logout')
        self.assertEqual(response.status_code, 401)
    
    def test_access_with_invalid_token(self):
        """Test accessing protected endpoints with invalid token"""
        
        # Invalid token format
        response = self.client.get(
            '/api/auth/me',
            HTTP_AUTHORIZATION='Bearer invalid.token.here'
        )
        self.assertEqual(response.status_code, 401)
        
        # Malformed authorization header
        response = self.client.get(
            '/api/auth/me',
            HTTP_AUTHORIZATION='InvalidFormat token'
        )
        self.assertEqual(response.status_code, 401)
    
    def test_jwt_token_structure(self):
        """Test that JWT tokens have correct structure and claims"""
        
        # Generate token manually
        token = JWTManager.generate_access_token(self.admin_user)
        payload = JWTManager.decode_token(token)
        
        # Verify required claims
        self.assertEqual(payload['user_id'], self.admin_user.id)
        self.assertEqual(payload['username'], self.admin_user.username)
        self.assertEqual(payload['type'], 'access')
        self.assertTrue(payload['is_staff'])
        self.assertTrue(payload['is_superuser'])
        self.assertIn('exp', payload)
        self.assertIn('iat', payload)
        
        # Test refresh token
        refresh_token = JWTManager.generate_refresh_token()
        refresh_payload = JWTManager.decode_token(refresh_token)
        
        self.assertEqual(refresh_payload['type'], 'refresh')
        self.assertIn('token_id', refresh_payload)
        self.assertIn('exp', refresh_payload)
        self.assertIn('iat', refresh_payload)