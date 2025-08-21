from django.contrib import admin
from django.utils import timezone
from .models import Room, TimeSlot


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_price', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['room', 'get_date_display', 'get_time_display', 'status']
    list_filter = ['status', 'date', 'room']
    search_fields = ['room__name']
    date_hierarchy = 'date'
    
    def get_date_display(self, obj):
        return obj.date.strftime('%d/%m/%Y') if obj.date else '-'
    get_date_display.short_description = 'Fecha'
    get_date_display.admin_order_field = 'date'
    
    def get_time_display(self, obj):
        return obj.time.strftime('%H:%M') if obj.time else '-'
    get_time_display.short_description = 'Hora'
    get_time_display.admin_order_field = 'time'