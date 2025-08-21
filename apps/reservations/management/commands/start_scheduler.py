from django.core.management.base import BaseCommand
from escape_rooms_backend.scheduler import start_scheduler
import signal
import sys


class Command(BaseCommand):
    help = 'Start the APScheduler for automatic reservation cancellation'

    def handle(self, *args, **options):
        self.stdout.write('Starting APScheduler...')
        
        scheduler = start_scheduler()
        
        def signal_handler(sig, frame):
            self.stdout.write('Shutting down scheduler...')
            scheduler.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.stdout.write(
            self.style.SUCCESS('APScheduler started successfully. Press Ctrl+C to stop.')
        )
        
        try:
            # Keep the process running
            while True:
                pass
        except KeyboardInterrupt:
            self.stdout.write('Shutting down scheduler...')
            scheduler.shutdown()