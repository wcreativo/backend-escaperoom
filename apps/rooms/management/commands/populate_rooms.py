from django.core.management.base import BaseCommand
from django.conf import settings
from apps.rooms.models import Room
import os


class Command(BaseCommand):
    help = 'Populate initial room data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frontend-url',
            type=str,
            help='Frontend URL for images (e.g., https://tu-frontend.onrender.com)',
        )

    def handle(self, *args, **options):
        # Get frontend URL from: 1) argument, 2) environment variable, 3) default
        frontend_url = (
            options.get('frontend_url') or 
            os.getenv('FRONTEND_URL') or 
            'https://tu-frontend.onrender.com'
        )
        
        # Clear existing rooms
        Room.objects.all().delete()
        
        # Room data based on reference materials
        rooms_data = [
            {
                'name': 'La Inquisición',
                'short_description': 'Escapa del sótano de la catedral y libérate de la santa inquisición en este ambiente del año 1700.',
                'full_description': 'Tú y tus amigos fueron capturados por los monjes y acusados de practicar brujeria. Deberán encontrar la forma de escapar del sótano de la catedral, resolver acertijos misteriosos, descifrar códigos y finalmente librarse de la santa inquisicion. Entre monjes y verdugos, este ambiente que te transporta al año 1700 te espera! Aplica tus poderes de hechicería y escapa lo más rápido posible! Lograrás hacerlo?',
                'base_price': 30.00,
                'hero_image_url': f'{frontend_url}/images/inquisicion-hero.jpg',
                'thumbnail_image_url': f'{frontend_url}/images/inquisicion-thumb.jpg',
            },
            {
                'name': 'El Purgatorio',
                'short_description': 'Adéntrate en las profundidades del purgatorio y encuentra tu camino hacia la redención.',
                'full_description': 'En las profundidades del purgatorio, las almas perdidas buscan su redención. Tú y tu equipo han sido enviados a este lugar entre el cielo y el infierno para completar una misión crucial. Deberán resolver enigmas ancestrales, superar pruebas de fe y encontrar las llaves que les permitirán ascender. El tiempo corre y las fuerzas oscuras no descansan. ¿Podrán purificar sus almas y encontrar el camino hacia la luz?',
                'base_price': 30.00,
                'hero_image_url': f'{frontend_url}/images/purgatorio-hero.jpg',
                'thumbnail_image_url': f'{frontend_url}/images/purgatorio-hero.jpg',
            }
        ]

        for room_data in rooms_data:
            room = Room.objects.create(
                name=room_data['name'],
                short_description=room_data['short_description'],
                full_description=room_data['full_description'],
                base_price=room_data['base_price'],
                is_active=True
            )
            
            # For now, we'll store the URLs directly in the database
            # In a production environment, you'd want to properly handle file uploads
            # But for development, we can reference the frontend static files
            if room_data.get('hero_image_url'):
                room.hero_image = room_data['hero_image_url']
            
            if room_data.get('thumbnail_image_url'):
                room.thumbnail_image = room_data['thumbnail_image_url']
            
            room.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created room: {room.name} with images')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated {Room.objects.count()} rooms')
        )