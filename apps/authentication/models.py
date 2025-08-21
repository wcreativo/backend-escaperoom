from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class RefreshToken(models.Model):
    """Model to store refresh tokens for JWT authentication"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'auth_refresh_tokens'
        ordering = ['-created_at']
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def deactivate(self):
        self.is_active = False
        self.save()
    
    def __str__(self):
        return f"RefreshToken for {self.user.username} - {self.token}"