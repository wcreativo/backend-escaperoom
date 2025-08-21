from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'room', 'time_slot', 'num_people', 
        'total_price', 'status', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'room']
    search_fields = ['customer_name', 'customer_email', 'customer_phone']
    readonly_fields = ['created_at', 'expires_at']
    date_hierarchy = 'created_at'
    
    def time_slot(self, obj):
        return f"{obj.time_slot.date} {obj.time_slot.time}"
    time_slot.short_description = 'Fecha y Hora'