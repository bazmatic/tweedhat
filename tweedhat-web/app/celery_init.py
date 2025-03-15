
import os
import logging
from celery import Celery

def init_celery(app=None):
    """Initialize Celery with enhanced logging."""
    # Configure Celery
    celery = Celery(
        app.import_name if app else 'tweedhat',
        broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    
    # Update Celery config
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        worker_hijack_root_logger=False,  # Don't hijack the root logger
        worker_redirect_stdouts=False,    # Don't redirect stdout/stderr
        task_track_started=True,          # Track when tasks are started
        task_send_sent_event=True,        # Send task-sent events
        worker_send_task_events=True,     # Send task events
        task_acks_late=True,              # Acknowledge tasks after execution
    )
    
    if app:
        celery.conf.update(app.config)
        
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    # Import celery_tasks to register the signal handlers
    import app.celery_tasks
    
    return celery
