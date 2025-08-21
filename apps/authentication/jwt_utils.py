import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from typing import Optional, Dict, Any
import uuid


class JWTManager:
    """Utility class for handling JWT tokens"""
    
    @staticmethod
    def generate_access_token(user: User) -> str:
        """Generate access token for user"""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'exp': datetime.utcnow() + timedelta(minutes=15),  # 15 minutes expiry
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def generate_refresh_token() -> str:
        """Generate refresh token"""
        payload = {
            'token_id': str(uuid.uuid4()),
            'exp': datetime.utcnow() + timedelta(days=7),  # 7 days expiry
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[Any, Any]]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """Get user from access token"""
        payload = JWTManager.decode_token(token)
        if not payload or payload.get('type') != 'access':
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
            return user
        except User.DoesNotExist:
            return None