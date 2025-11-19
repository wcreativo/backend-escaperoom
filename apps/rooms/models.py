from django.db import models
from django.utils.text import slugify


class Room(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.TextField(max_length=200)
    full_description = models.TextField()
    hero_image = models.URLField(max_length=500, blank=True, null=True)
    thumbnail_image = models.URLField(max_length=500, blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True, null=True)
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
        ordering = ['date', 'time']
        indexes = [
            models.Index(fields=['room', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['date', 'time']),
        ]
        constraints = [
            # Unique constraint for active time slots only
            models.UniqueConstraint(
                fields=['room', 'date', 'time', 'status'],
                condition=models.Q(status='active') | models.Q(status='reserved'),
                name='unique_active_timeslot'
            ),
            # Basic unique constraint for room, date, time combination
            models.UniqueConstraint(
                fields=['room', 'date', 'time'],
                name='unique_room_datetime'
            ),
        ]

    def __str__(self):
        return f"{self.room.name} - {self.date} {self.time} ({self.get_status_display()})"