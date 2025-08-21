from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json
import jwt
from django.conf import settings

from .models import RefreshToken
from .jwt_utils import JWTManager


class JWTManagerTest(TestCase):
    """Test JWT utility functions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            password='testpass123',
            is_staff=True
        )
    
    def test_generate_access_token(self):
        """Test access token generation"""
        token = JWTManager.generate_access_token(self.user)
        self.assertIsInstance(token, str)
        
        # Decode and verify payload
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['user_id'], self.user.id)
        self.assertEqual(payload['username'], self.user.username)
        self.assertEqual(payload['type'], 'access')
        self.assertTrue(payload['is_staff'])
    
    def test_generate_refresh_token(self):
        """Test refresh token generation"""
        token = JWTManager.generate_refresh_token()
        self.assertIsInstance(token, str)
        
        # Decode and verify payload
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['type'], 'refresh')
        self.assertIn('token_id', payload)
    
    def test_decode_valid_token(self):
        """Test decoding valid token"""
        token = JWTManager.generate_access_token(self.user)
        payload = JWTManager.decode_token(token)
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user_id'], self.user.id)
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        payload = JWTManager.decode_token(invalid_token)
        self.assertIsNone(payload)
    
    def test_get_user_from_token(self):
        """Test getting user from valid token"""
        token = JWTManager.generate_access_token(self.user)
        user = JWTManager.get_user_from_token(token)
        
        self.assertEqual(user, self.user)
    
    def test_get_user_from_invalid_token(self):
        """Test getting user from invalid token"""
        invalid_token = "invalid.token.here"
        user = JWTManager.get_user_from_token(invalid_token)
        self.assertIsNone(user)


class RefreshTokenModelTest(TestCase):
    """Test RefreshToken model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            password='testpass123',
            is_staff=True
        )
    
    def test_create_refresh_token(self):
        """Test creating refresh token"""
        token = RefreshToken.objects.create(
            user=self.user,
            token='test-token-id',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.token, 'test-token-id')
        self.assertTrue(token.is_active)
    
    def test_is_expired(self):
        """Test token expiration check"""
        # Create expired token
        expired_token = RefreshToken.objects.create(
            user=self.user,
            token='expired-token',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # Create valid token
        valid_token = RefreshToken.objects.create(
            user=self.user,
            token='valid-token',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertTrue(expired_token.is_expired())
        self.assertFalse(valid_token.is_expired())
    
    def test_deactivate_token(self):
        """Test token deactivation"""
        token = RefreshToken.objects.create(
            user=self.user,
            token='test-token',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertTrue(token.is_active)
        token.deactivate()
        self.assertFalse(token.is_active)


class AuthenticationAPITest(TestCase):
    """Test authentication API endpoints"""
    
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='testpass123',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='regularuser',
            password='testpass123',
            is_staff=False
        )
    
    def test_login_success_staff_user(self):
        """Test successful login with staff user"""
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'staffuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertEqual(data['token_type'], 'Bearer')
        self.assertEqual(data['expires_in'], 900)
        
        # Verify refresh token was stored in database
        self.assertTrue(RefreshToken.objects.filter(user=self.staff_user).exists())
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'staffuser',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'invalid_credentials')
    
    def test_login_non_staff_user(self):
        """Test login with non-staff user"""
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'regularuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'insufficient_permissions')
    
    def test_refresh_token_success(self):
        """Test successful token refresh"""
        # First login to get tokens
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'staffuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        
        login_data = login_response.json()
        refresh_token = login_data['refresh_token']
        
        # Use refresh token to get new access token
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
        self.assertEqual(refresh_data['expires_in'], 900)
    
    def test_refresh_token_invalid(self):
        """Test refresh with invalid token"""
        response = self.client.post(
            '/api/auth/refresh',
            data=json.dumps({
                'refresh_token': 'invalid.token.here'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'invalid_token')
    
    def test_logout_success(self):
        """Test successful logout"""
        # First login to get tokens
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'staffuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        
        login_data = login_response.json()
        access_token = login_data['access_token']
        
        # Logout
        logout_response = self.client.post(
            '/api/auth/logout',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        self.assertEqual(logout_response.status_code, 200)
        
        # Verify all refresh tokens are deactivated
        active_tokens = RefreshToken.objects.filter(user=self.staff_user, is_active=True)
        self.assertEqual(active_tokens.count(), 0)
    
    def test_logout_without_auth(self):
        """Test logout without authentication"""
        response = self.client.post('/api/auth/logout')
        self.assertEqual(response.status_code, 401)
    
    def test_get_user_info_success(self):
        """Test getting user info with valid token"""
        # First login to get token
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'staffuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        
        login_data = login_response.json()
        access_token = login_data['access_token']
        
        # Get user info
        response = self.client.get(
            '/api/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['id'], self.staff_user.id)
        self.assertEqual(data['username'], 'staffuser')
        self.assertTrue(data['is_staff'])
    
    def test_get_user_info_without_auth(self):
        """Test getting user info without authentication"""
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 401)
    
    def test_get_user_info_invalid_token(self):
        """Test getting user info with invalid token"""
        response = self.client.get(
            '/api/auth/me',
            HTTP_AUTHORIZATION='Bearer invalid.token.here'
        )
        self.assertEqual(response.status_code, 401)


class JWTAuthMiddlewareTest(TestCase):
    """Test JWT authentication middleware"""
    
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='testpass123',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='regularuser',
            password='testpass123',
            is_staff=False
        )
    
    def test_authenticate_valid_staff_token(self):
        """Test authentication with valid staff token"""
        from .middleware import jwt_auth
        from django.http import HttpRequest
        
        token = JWTManager.generate_access_token(self.staff_user)
        request = HttpRequest()
        
        user = jwt_auth.authenticate(request, token)
        self.assertEqual(user, self.staff_user)
    
    def test_authenticate_valid_non_staff_token(self):
        """Test authentication with valid non-staff token"""
        from .middleware import jwt_auth
        from django.http import HttpRequest
        
        token = JWTManager.generate_access_token(self.regular_user)
        request = HttpRequest()
        
        user = jwt_auth.authenticate(request, token)
        self.assertIsNone(user)  # Should return None for non-staff users
    
    def test_authenticate_invalid_token(self):
        """Test authentication with invalid token"""
        from .middleware import jwt_auth
        from django.http import HttpRequest
        
        request = HttpRequest()
        
        user = jwt_auth.authenticate(request, 'invalid.token.here')
        self.assertIsNone(user)