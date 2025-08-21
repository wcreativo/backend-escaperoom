from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.http import HttpRequest
from .jwt_utils import JWTManager
from typing import Optional


class JWTAuth(HttpBearer):
    """JWT Authentication for Django Ninja"""
    
    def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        """Authenticate user using JWT token"""
        user = JWTManager.get_user_from_token(token)
        if user and user.is_staff:  # Only allow staff users for admin endpoints
            return user
        return None


# Create instance to use in API endpoints
jwt_auth = JWTAuth()