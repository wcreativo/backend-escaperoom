from django.core.management.base import BaseCommand
from django.core.files import File
from apps.rooms.models import Room
import os


class Command(BaseCommand):
    help = 'Populate initial room data'

    def handle(self, *args, **options):
        # Clear existing rooms
        Room.objects.all().delete()
        
        # Room data based on reference materials
        rooms_data = [
            {
                'name': 'La Inquisición',
                'short_description': 'Escapa del sótano de la catedral y libérate de la santa inquisición en este ambiente del año 1700.',
                'full_description': 'Tú y tus amigos fueron capturados por los monjes y acusados de practicar brujeria. Deberán encontrar la forma de escapar del sótano de la catedral, resolver acertijos misteriosos, descifrar códigos y finalmente librarse de la santa inquisicion. Entre monjes y verdugos, este ambiente que te transporta al año 1700 te espera! Aplica tus poderes de hechicería y escapa lo más rápido posible! Lograrás hacerlo?',
                'base_price': 30.00,
                'hero_image_path': 'reference_data/images/inquisicion.png',
                'thumbnail_image_path': 'reference_data/images/inquisicion.png',
            },
            {
                'name': 'El Purgatorio',
                'short_description': 'Adéntrate en las profundidades del purgatorio y encuentra tu camino hacia la redención.',
                'full_description': 'En las profundidades del purgatorio, las almas perdidas buscan su redención. Tú y tu equipo han sido enviados a este lugar entre el cielo y el infierno para completar una misión crucial. Deberán resolver enigmas ancestrales, superar pruebas de fe y encontrar las llaves que les permitirán ascender. El tiempo corre y las fuerzas oscuras no descansan. ¿Podrán purificar sus almas y encontrar el camino hacia la luz?',
                'base_price': 30.00,
                'hero_image_path': 'reference_data/images/purgatorio.png',
                'thumbnail_image_path': 'reference_data/images/purgatorio.png',
            },
            {
                'name': 'El Laboratorio Secreto',
                'short_description': 'Descubre los secretos de un laboratorio abandonado lleno de experimentos misteriosos.',
                'full_description': 'Un científico loco ha desaparecido dejando atrás su laboratorio lleno de experimentos peligrosos. Como equipo de investigación, deben infiltrarse en el laboratorio, descifrar sus notas científicas, resolver complejos acertijos químicos y detener el experimento que podría destruir la ciudad. Entre tubos de ensayo, fórmulas misteriosas y dispositivos extraños, tendrán que usar su ingenio para salvar el día. El reloj marca el tiempo límite antes de que sea demasiado tarde.',
                'base_price': 30.00,
                'hero_image_path': None,  # Will use a placeholder
                'thumbnail_image_path': None,
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
            
            # Copy images if they exist
            if room_data['hero_image_path'] and os.path.exists(room_data['hero_image_path']):
                with open(room_data['hero_image_path'], 'rb') as f:
                    room.hero_image.save(
                        f"{room.slug}_hero.png",
                        File(f),
                        save=False
                    )
            
            if room_data['thumbnail_image_path'] and os.path.exists(room_data['thumbnail_image_path']):
                with open(room_data['thumbnail_image_path'], 'rb') as f:
                    room.thumbnail_image.save(
                        f"{room.slug}_thumb.png",
                        File(f),
                        save=False
                    )
            
            room.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created room: {room.name}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated {Room.objects.count()} rooms')
        )