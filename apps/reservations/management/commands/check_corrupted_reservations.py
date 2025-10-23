from django.core.management.base import BaseCommand
from django.db import transaction
from apps.reservations.models import Reservation


class Command(BaseCommand):
    help = 'Check for corrupted reservation data and optionally fix it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix corrupted data instead of just reporting it',
        )

    def handle(self, *args, **options):
        self.stdout.write('Checking for corrupted reservation data...')
        
        corrupted_count = 0
        fixed_count = 0
        
        # Check all reservations
        for reservation in Reservation.objects.all():
            issues = []
            
            # Check for null/empty required fields
            if not reservation.customer_name:
                issues.append('customer_name is null/empty')
            if not reservation.customer_email:
                issues.append('customer_email is null/empty')
            if not reservation.customer_phone:
                issues.append('customer_phone is null/empty')
            if not reservation.num_people:
                issues.append('num_people is null/zero')
            if not reservation.total_price:
                issues.append('total_price is null/zero')
            if not reservation.status:
                issues.append('status is null/empty')
            
            # Check for broken foreign keys
            if not reservation.room:
                issues.append('room foreign key is broken')
            if not reservation.time_slot:
                issues.append('time_slot foreign key is broken')
            
            if issues:
                corrupted_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Reservation {reservation.id}: {", ".join(issues)}'
                    )
                )
                
                if options['fix']:
                    try:
                        with transaction.atomic():
                            # Fix null/empty fields with defaults
                            if not reservation.customer_name:
                                reservation.customer_name = 'DATOS CORRUPTOS'
                            if not reservation.customer_email:
                                reservation.customer_email = 'corrupted@example.com'
                            if not reservation.customer_phone:
                                reservation.customer_phone = '000000000'
                            if not reservation.num_people:
                                reservation.num_people = 1
                            if not reservation.total_price:
                                reservation.total_price = 0.0
                            if not reservation.status:
                                reservation.status = 'cancelled'
                            
                            # For broken foreign keys, we might need to delete the reservation
                            if not reservation.room or not reservation.time_slot:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'Deleting reservation {reservation.id} due to broken foreign keys'
                                    )
                                )
                                reservation.delete()
                            else:
                                reservation.save()
                            
                            fixed_count += 1
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Failed to fix reservation {reservation.id}: {str(e)}'
                            )
                        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Found {corrupted_count} corrupted reservations'
            )
        )
        
        if options['fix']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Fixed/removed {fixed_count} corrupted reservations'
                )
            )
        else:
            self.stdout.write(
                'Run with --fix to attempt to fix the corrupted data'
            )