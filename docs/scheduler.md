# APScheduler for Automatic Reservation Cancellation

This document describes the APScheduler implementation for automatically cancelling expired reservations in the escape room booking system.

## Overview

The scheduler automatically cancels reservations that have been pending for more than 30 minutes, freeing up the associated time slots for new bookings.

## Features

- **Automatic Cancellation**: Cancels reservations that expire after 30 minutes
- **Time Slot Management**: Automatically frees up time slots when reservations are cancelled
- **Robust Error Handling**: Continues processing even if individual reservations fail
- **Comprehensive Logging**: Logs all cancellation activities for monitoring
- **Atomic Operations**: Uses database transactions to ensure data consistency
- **Configurable**: Can run as background service or dedicated worker

## Components

### 1. Scheduler Module (`escape_rooms_backend/scheduler.py`)

Main functions:
- `cancel_expired_reservations()`: Core function that finds and cancels expired reservations
- `start_scheduler(blocking=False, config=None)`: Starts the scheduler
- `stop_scheduler(scheduler)`: Safely stops the scheduler
- `get_scheduler()`: Returns singleton background scheduler instance

### 2. Management Command (`apps/reservations/management/commands/start_scheduler.py`)

Django management command to run the scheduler as a dedicated worker process.

### 3. App Configuration (`apps/reservations/apps.py`)

Automatically starts background scheduler when Django app starts (except during migrations/tests).

## Usage

### Option 1: Background Mode (Integrated with Django)

The scheduler automatically starts when Django starts up. No additional action needed.

```python
# The scheduler starts automatically via apps.py
# Jobs run every minute in the background
```

### Option 2: Dedicated Worker Process

Run as a separate process for production environments:

```bash
# Start dedicated scheduler worker
python manage.py start_scheduler

# The worker will run continuously until stopped with Ctrl+C
```

### Option 3: Manual Control

```python
from escape_rooms_backend.scheduler import start_scheduler, stop_scheduler

# Start background scheduler
scheduler = start_scheduler(blocking=False)

# Start blocking scheduler (for dedicated worker)
scheduler = start_scheduler(blocking=True)

# Stop scheduler
stop_scheduler(scheduler)
```

## Configuration

### Settings (`config/settings/base.py`)

```python
# APScheduler configuration
SCHEDULER_CONFIG = {
    'apscheduler.jobstores.default': {
        'type': 'sqlalchemy',
        'url': 'sqlite:///jobs.sqlite'
    },
    'apscheduler.executors.default': {
        'type': 'threadpool',
        'max_workers': 20
    },
    'apscheduler.job_defaults.coalesce': False,
    'apscheduler.job_defaults.max_instances': 3,
    'apscheduler.timezone': TIME_ZONE,
}

# Set to True when running as dedicated worker
SCHEDULER_WORKER_MODE = False
```

### Environment Variables

```bash
# Disable background scheduler (run as dedicated worker instead)
SCHEDULER_WORKER_MODE=true
```

## Job Details

- **Job ID**: `cancel_expired_reservations`
- **Schedule**: Every 1 minute
- **Max Instances**: 1 (prevents overlapping executions)
- **Coalesce**: True (combines missed executions)

## Logging

The scheduler logs to the `escape_rooms_backend.scheduler` logger:

- **INFO**: Successful cancellations and scheduler start/stop
- **DEBUG**: When no expired reservations are found
- **ERROR**: Database errors or scheduler failures

Example log output:
```
INFO 2025-08-21 06:20:10,066 scheduler Cancelled expired reservation 123 for John Doe - Test Room on 2025-08-21 at 14:30:00
INFO 2025-08-21 06:20:10,066 scheduler Successfully cancelled 1 expired reservations
```

## Database Schema

The scheduler works with these models:

### Reservation Model
- `status`: 'pending', 'paid', 'cancelled'
- `expires_at`: DateTime when reservation expires
- `is_expired`: Property that checks if reservation is expired

### TimeSlot Model
- `status`: 'active', 'reserved'

## Error Handling

- **Database Errors**: Logged but don't stop the scheduler
- **Individual Reservation Errors**: Logged and skipped, processing continues
- **Scheduler Startup Errors**: Logged and re-raised
- **Graceful Shutdown**: Handles SIGINT and SIGTERM signals

## Testing

### Unit Tests
```bash
python manage.py test apps.reservations.test_scheduler
```

### Integration Tests
```bash
python manage.py test apps.reservations.test_scheduler_integration
```

### Manual Testing
```bash
python manage.py shell < test_scheduler_manual.py
```

## Production Deployment

### Recommended Setup

1. **Web Server**: Run Django with background scheduler disabled
   ```bash
   export SCHEDULER_WORKER_MODE=true
   python manage.py runserver
   ```

2. **Scheduler Worker**: Run dedicated scheduler process
   ```bash
   python manage.py start_scheduler
   ```

3. **Process Management**: Use supervisor, systemd, or similar to manage the scheduler process

### Systemd Service Example

```ini
[Unit]
Description=Escape Room Scheduler
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/backend
Environment=DJANGO_SETTINGS_MODULE=escape_rooms_backend.settings
ExecStart=/path/to/venv/bin/python manage.py start_scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Monitoring

Monitor the scheduler by:

1. **Log Files**: Check application logs for scheduler activity
2. **Database**: Monitor job execution in the SQLAlchemy job store
3. **Process Status**: Ensure scheduler process is running
4. **Reservation Status**: Verify expired reservations are being cancelled

## Troubleshooting

### Common Issues

1. **Scheduler Not Starting**
   - Check SQLAlchemy is installed: `pip install SQLAlchemy`
   - Verify database permissions for job store
   - Check configuration syntax

2. **Jobs Not Running**
   - Verify scheduler is actually started
   - Check for errors in logs
   - Ensure no overlapping job instances

3. **Database Locks**
   - Use atomic transactions (already implemented)
   - Monitor for long-running queries
   - Consider connection pooling

### Debug Commands

```python
# Check if scheduler is running
from escape_rooms_backend.scheduler import get_scheduler
scheduler = get_scheduler()
print(f"Running: {scheduler.running}")
print(f"Jobs: {scheduler.get_jobs()}")

# Manually run cancellation
from escape_rooms_backend.scheduler import cancel_expired_reservations
cancel_expired_reservations()

# Check expired reservations
from apps.reservations.models import Reservation
from django.utils import timezone
expired = Reservation.objects.filter(
    status='pending',
    expires_at__lt=timezone.now()
)
print(f"Expired reservations: {expired.count()}")
```