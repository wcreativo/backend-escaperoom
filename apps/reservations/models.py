from django.db import models
from django.utils import timezone
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

    def __str__(self):
        return f"{self.customer_name} - {self.room.name} - {self.time_slot.date} {self.time_slot.time}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at and self.status == 'pending'

    def calculate_total_price(self):
        """Calculate total price based on number of people"""
        if self.num_people <= 3:
            price_per_person = 30.00
        else:
            price_per_person = 25.00
        return self.num_people * price_per_person