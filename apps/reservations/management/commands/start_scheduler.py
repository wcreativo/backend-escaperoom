from django.core.management.base import BaseCommand
from escape_rooms_backend.scheduler import start_scheduler, stop_scheduler
import signal
import sys
import time


class Command(BaseCommand):
    help = 'Start the APScheduler for automatic reservation cancellation as a dedicated worker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=1,
            help='Interval in minutes between job executions (default: 1)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting APScheduler as dedicated worker...')
        
        scheduler = None
        
        def signal_handler(sig, frame):
            self.stdout.write('\nReceived shutdown signal. Stopping scheduler...')
            if scheduler:
                stop_scheduler(scheduler)
            self.stdout.write(self.style.SUCCESS('Scheduler stopped successfully.'))
            sys.exit(0)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start scheduler in blocking mode (dedicated worker)
            scheduler = start_scheduler(blocking=True)
            
            self.stdout.write(
                self.style.SUCCESS(
                    'APScheduler started successfully as dedicated worker.\n'
                    'Jobs will run every minute to cancel expired reservations.\n'
                    'Press Ctrl+C to stop.'
                )
            )
            
            # Keep the process running (blocking scheduler handles this)
            # This is just a fallback in case the blocking scheduler exits
            while scheduler.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stdout.write('\nShutting down scheduler...')
            if scheduler:
                stop_scheduler(scheduler)
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error running scheduler: {e}')
            )
            if scheduler:
                stop_scheduler(scheduler)
            sys.exit(1)