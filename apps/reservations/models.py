from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from apps.rooms.models import Room, TimeSlot


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente de Pago'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='reservations')
    time_slot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE, related_name='reservation')
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    num_people = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['room', 'status']),
        ]

    def __str__(self):
        return f"{self.customer_name} - {self.room.name} - {self.time_slot.date} {self.time_slot.time}"

    def clean(self):
        """Validate that the time slot is available"""
        if self.time_slot and self.time_slot.status != 'active':
            raise ValidationError('The selected time slot is not available.')
        
        if self.time_slot and self.time_slot.room != self.room:
            raise ValidationError('Time slot must belong to the selected room.')

    def save(self, *args, **kwargs):
        # Only perform full validation and time slot updates for new reservations
        # or when not using update_fields
        update_fields = kwargs.get('update_fields')
        is_new = self._state.adding
        
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        
        # Auto-calculate total price if not set
        if not self.total_price:
            self.total_price = self.calculate_total_price()
        
        # Only validate and update time slot for new reservations or full saves
        if is_new or update_fields is None:
            # Validate before saving
            self.full_clean()
            
            # Mark time slot as reserved for new reservations
            if is_new and self.time_slot and self.time_slot.status == 'active':
                self.time_slot.status = 'reserved'
                self.time_slot.save()
        
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at and self.status == 'pending'

    def calculate_total_price(self):
        """Calculate total price based on number of people
        
        Pricing rules:
        - 1-3 people: $30 per person
        - 4+ people: $25 per person
        """
        if self.num_people <= 3:
            price_per_person = 30.00
        else:
            price_per_person = 25.00
        return self.num_people * price_per_person

    def cancel_reservation(self):
        """Cancel the reservation and free up the time slot"""
        if self.status != 'cancelled':
            self.status = 'cancelled'
            if self.time_slot:
                self.time_slot.status = 'active'
                self.time_slot.save()
            # Use update_fields to avoid triggering full_clean validation
            self.save(update_fields=['status'])