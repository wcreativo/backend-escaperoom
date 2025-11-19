#!/usr/bin/env python
"""
Simple script to clean up expired reservations manually.
Can be run as a cron job or manually when needed.
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'escape_rooms_backend.settings.development')
django.setup()

from django.core.management import call_command

if __name__ == "__main__":
    print("🧹 Running reservation cleanup...")
    
    # Check if dry-run argument is passed
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        call_command('cleanup_expired_reservations', '--dry-run')
    else:
        call_command('cleanup_expired_reservations')
    
    print("✅ Cleanup completed!")