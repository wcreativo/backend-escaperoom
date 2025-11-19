"""
Management command to manually clean up expired reservations.
This replaces the automatic scheduler for cleanup tasks.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from apps.reservations.models import Reservation


class Command(BaseCommand):
    help = 'Cancel expired reservations and free up their time slots'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cancelled without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Find expired reservations
        expired_reservations = Reservation.objects.select_related('time_slot', 'room').filter(
            status='pending',
            expires_at__lt=timezone.now()
        )
        
        count = expired_reservations.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired reservations found.')
            )
            return
        
        self.stdout.write(f'Found {count} expired reservation(s):')
        
        cancelled_count = 0
        
        for reservation in expired_reservations:
            self.stdout.write(
                f'  - ID {reservation.id}: {reservation.customer_name} - '
                f'{reservation.room.name} on {reservation.time_slot.date} '
                f'at {reservation.time_slot.time} (expired: {reservation.expires_at})'
            )
            
            if not dry_run:
                try:
                    with transaction.atomic():
                        reservation.cancel_reservation()
                        cancelled_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'    ✓ Cancelled reservation {reservation.id}')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'    ✗ Error cancelling reservation {reservation.id}: {e}')
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully cancelled {cancelled_count} expired reservations.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'\nWould cancel {count} expired reservations (use without --dry-run to execute).')
            )