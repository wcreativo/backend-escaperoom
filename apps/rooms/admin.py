from django.contrib import admin
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
    list_display = ['room', 'date', 'time', 'status']
    list_filter = ['status', 'date', 'room']
    search_fields = ['room__name']
    date_hierarchy = 'date'