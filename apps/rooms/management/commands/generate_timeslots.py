from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time, timedelta
from apps.rooms.models import Room, TimeSlot


class Command(BaseCommand):
    help = 'Generate time slots for all rooms based on schedule'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to generate slots for (default: 30)'
        )

    def handle(self, *args, **options):
        days_ahead = options['days']
        
        # Schedule according to requirements:
        # Monday-Thursday: 12:00 PM to 9:00 PM
        # Friday: 12:00 PM to 10:00 PM  
        # Saturday: 10:00 AM to 10:00 PM
        # Sunday: 10:00 AM to 9:00 PM
        
        schedule = {
            0: (time(12, 0), time(21, 0)),  # Monday
            1: (time(12, 0), time(21, 0)),  # Tuesday
            2: (time(12, 0), time(21, 0)),  # Wednesday
            3: (time(12, 0), time(21, 0)),  # Thursday
            4: (time(12, 0), time(22, 0)),  # Friday
            5: (time(10, 0), time(22, 0)),  # Saturday
            6: (time(10, 0), time(21, 0)),  # Sunday
        }
        
        # Clear existing time slots
        TimeSlot.objects.all().delete()
        
        rooms = Room.objects.filter(is_active=True)
        if not rooms.exists():
            self.stdout.write(
                self.style.ERROR('No active rooms found. Please run populate_rooms first.')
            )
            return
        
        slots_created = 0
        start_date = timezone.now().date()
        
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            weekday = current_date.weekday()
            
            if weekday in schedule:
                start_time, end_time = schedule[weekday]
                
                # Generate hourly slots
                current_time = start_time
                while current_time < end_time:
                    for room in rooms:
                        TimeSlot.objects.create(
                            room=room,
                            date=current_date,
                            time=current_time,
                            status='active'
                        )
                        slots_created += 1
                    
                    # Move to next hour
                    current_hour = current_time.hour + 1
                    if current_hour < 24:
                        current_time = time(current_hour, 0)
                    else:
                        break
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {slots_created} time slots for {rooms.count()} rooms over {days_ahead} days'
            )
        )