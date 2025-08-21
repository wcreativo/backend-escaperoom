from django.core.management.base import BaseCommand
from apps.rooms.models import Room


class Command(BaseCommand):
    help = 'Check room data including video URLs'

    def handle(self, *args, **options):
        rooms = Room.objects.all()
        
        if not rooms.exists():
            self.stdout.write(
                self.style.WARNING('No rooms found in database.')
            )
            return
        
        for room in rooms:
            self.stdout.write(f"\nRoom: {room.name}")
            self.stdout.write(f"  ID: {room.id}")
            self.stdout.write(f"  Hero Image: {room.hero_image}")
            self.stdout.write(f"  Video URL: {room.video_url}")
            self.stdout.write(f"  Is Active: {room.is_active}")
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal rooms: {rooms.count()}')
        )