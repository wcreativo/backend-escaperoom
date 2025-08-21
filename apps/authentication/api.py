from ninja import Router
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.http import HttpRequest
from .schemas import (
    LoginSchema, 
    TokenResponseSchema, 
    RefreshTokenSchema, 
    AccessTokenResponseSchema,
    ErrorSchema,
    UserInfoSchema
)
from .models import RefreshToken
from .jwt_utils import JWTManager
from .middleware import jwt_auth

router = Router()


@router.post("/login", response={200: TokenResponseSchema, 401: ErrorSchema})
def login(request: HttpRequest, credentials: LoginSchema):
    """
    Authenticate admin user and return JWT tokens
    """
    user = authenticate(username=credentials.username, password=credentials.password)
    
    if not user:
        return 401, {"error": "invalid_credentials", "message": "Invalid username or password"}
    
    if not user.is_staff:
        return 401, {"error": "insufficient_permissions", "message": "User must be staff to access admin panel"}
    
    # Generate tokens
    access_token = JWTManager.generate_access_token(user)
    refresh_token_jwt = JWTManager.generate_refresh_token()
    
    # Decode refresh token to get token_id
    refresh_payload = JWTManager.decode_token(refresh_token_jwt)
    
    # Store refresh token in database
    refresh_token_obj = RefreshToken.objects.create(
        user=user,
        token=refresh_payload['token_id'],
        expires_at=timezone.now() + timedelta(days=7)
    )
    
    return 200, {
        "access_token": access_token,
        "refresh_token": refresh_token_jwt,
        "token_type": "Bearer",
        "expires_in": 900
    }


@router.post("/refresh", response={200: AccessTokenResponseSchema, 401: ErrorSchema})
def refresh_token(request: HttpRequest, token_data: RefreshTokenSchema):
    """
    Refresh access token using refresh token
    """
    # Decode refresh token
    payload = JWTManager.decode_token(token_data.refresh_token)
    
    if not payload or payload.get('type') != 'refresh':
        return 401, {"error": "invalid_token", "message": "Invalid refresh token"}
    
    # Find refresh token in database
    try:
        token_id = payload.get('token_id')
        refresh_token_obj = RefreshToken.objects.get(
            token=token_id,
            is_active=True
        )
        
        if refresh_token_obj.is_expired():
            refresh_token_obj.deactivate()
            return 401, {"error": "token_expired", "message": "Refresh token has expired"}
        
        # Generate new access token
        access_token = JWTManager.generate_access_token(refresh_token_obj.user)
        
        return 200, {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 900
        }
        
    except RefreshToken.DoesNotExist:
        return 401, {"error": "invalid_token", "message": "Refresh token not found"}


@router.post("/logout", auth=jwt_auth, response={200: dict, 401: ErrorSchema})
def logout(request: HttpRequest):
    """
    Logout user by deactivating all refresh tokens
    """
    user = request.auth
    
    # Deactivate all refresh tokens for the user
    RefreshToken.objects.filter(user=user, is_active=True).update(is_active=False)
    
    return 200, {"message": "Successfully logged out"}


@router.get("/me", auth=jwt_auth, response={200: UserInfoSchema, 401: ErrorSchema})
def get_user_info(request: HttpRequest):
    """
    Get current user information
    """
    user = request.auth
    
    return 200, {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser
    }