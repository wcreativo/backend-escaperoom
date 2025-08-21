from django.db import models
from django.utils.text import slugify


class Room(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.TextField(max_length=200)
    full_description = models.TextField()
    hero_image = models.ImageField(upload_to='rooms/hero/', blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to='rooms/thumbs/', blank=True, null=True)
    base_price = models.DecimalField(max_digits=6, decimal_places=2, default=30.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TimeSlot(models.Model):
    STATUS_CHOICES = [
        ('active', 'Activa'),
        ('reserved', 'Reservada'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['room', 'date', 'time']
        ordering = ['date', 'time']
        indexes = [
            models.Index(fields=['room', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['date', 'time']),
        ]

    def __str__(self):
        return f"{self.room.name} - {self.date} {self.time} ({self.get_status_display()})"