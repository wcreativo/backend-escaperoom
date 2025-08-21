from django.contrib import admin
from django.utils import timezone
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'room', 'get_time_slot_display', 'num_people', 
        'total_price', 'status', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'room']
    search_fields = ['customer_name', 'customer_email', 'customer_phone']
    readonly_fields = ['created_at', 'expires_at']
    date_hierarchy = 'created_at'
    
    def get_time_slot_display(self, obj):
        if obj.time_slot:
            # Combine date and time into a proper datetime object
            datetime_obj = timezone.datetime.combine(
                obj.time_slot.date, 
                obj.time_slot.time
            )
            # Make it timezone aware
            datetime_obj = timezone.make_aware(datetime_obj)
            # Format it nicely
            return datetime_obj.strftime('%d/%m/%Y %H:%M')
        return '-'
    get_time_slot_display.short_description = 'Fecha y Hora'
    get_time_slot_display.admin_order_field = 'time_slot__date'