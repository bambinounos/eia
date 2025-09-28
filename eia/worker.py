from celery import Celery
from .config import settings

# Check if settings are loaded
if not settings:
    raise RuntimeError("Application settings could not be loaded. Aborting worker setup.")

# Create the Celery application instance.
# The first argument is the name of the current module.
# The 'broker' argument specifies the URL of the message broker (Redis).
# The 'backend' argument specifies the URL of the result backend (also Redis).
celery_app = Celery(
    "eia_worker",
    broker=settings.redis.url,
    backend=settings.redis.url,
    include=["eia.tasks"]  # List of modules to import when the worker starts.
)

# Optional Celery configuration
celery_app.conf.update(
    task_track_started=True,
    # You can add more Celery settings here if needed
)

# --- Celery Beat Periodic Task Scheduling ---
# This section configures Celery Beat to run tasks on a schedule.

# Load the scan interval from the application settings
scan_interval_seconds = settings.imap.scan_interval_minutes * 60

celery_app.conf.beat_schedule = {
    # The name of the schedule entry
    'scan-emails-periodically': {
        # The task to run (the string path to the task function)
        'task': 'eia.tasks.process_all_accounts_task',
        # The schedule (e.g., run every `scan_interval_seconds` seconds)
        'schedule': scan_interval_seconds,
        # Optional arguments to pass to the task
        'args': (),
    },
}

# You can add more scheduled tasks here if needed.

# To run the worker:
# celery -A eia.worker.celery_app worker --loglevel=info

# To run the scheduler (Celery Beat):
# celery -A eia.worker.celery_app beat --loglevel=info