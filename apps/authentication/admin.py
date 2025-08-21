from django.contrib import admin
from .models import RefreshToken


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    """Admin interface for RefreshToken model"""
    
    list_display = ('user', 'token_short', 'created_at', 'expires_at', 'is_active', 'is_expired')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('token', 'created_at')
    ordering = ('-created_at',)
    
    def token_short(self, obj):
        """Display shortened token for readability"""
        return f"{obj.token[:8]}...{obj.token[-8:]}" if len(obj.token) > 16 else obj.token
    token_short.short_description = 'Token (shortened)'
    
    def is_expired(self, obj):
        """Display if token is expired"""
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    actions = ['deactivate_tokens']
    
    def deactivate_tokens(self, request, queryset):
        """Admin action to deactivate selected tokens"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f'{count} tokens were deactivated.')
    deactivate_tokens.short_description = 'Deactivate selected tokens'