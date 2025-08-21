from ninja import Schema
from typing import Optional


class LoginSchema(Schema):
    """Schema for login request"""
    username: str
    password: str


class TokenResponseSchema(Schema):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes in seconds


class RefreshTokenSchema(Schema):
    """Schema for refresh token request"""
    refresh_token: str


class AccessTokenResponseSchema(Schema):
    """Schema for access token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes in seconds


class ErrorSchema(Schema):
    """Schema for error responses"""
    error: str
    message: str


class UserInfoSchema(Schema):
    """Schema for user information"""
    id: int
    username: str
    email: str
    is_staff: bool
    is_superuser: bool