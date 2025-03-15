#!/usr/bin/env python3

import os
import sys
import logging
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tweedhat-web/tweedhat-web.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_enhanced_logging():
    """
    Set up enhanced logging for the TweedHat application.
    This function modifies the logging configuration to provide more detailed job progress information.
    """
    logger.info("Setting up enhanced job logging for TweedHat")
    
    # Create a celery_tasks.py file with enhanced logging
    celery_tasks_path = "tweedhat-web/app/celery_tasks.py"
    
    with open(celery_tasks_path, 'w') as f:
        f.write('''
import os
import logging
from celery.signals import task_prerun, task_postrun, task_success, task_failure, task_revoked
from celery.utils.log import get_task_logger

# Set up logging
logger = get_task_logger(__name__)

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **_):
    """Log when a task starts."""
    logger.info(f"TASK STARTED: {task.name}[{task_id}] - Args: {args}")

@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **_):
    """Log when a task completes."""
    logger.info(f"TASK COMPLETED: {task.name}[{task_id}] - State: {state}")

@task_success.connect
def task_success_handler(sender, result, **_):
    """Log when a task succeeds."""
    logger.info(f"TASK SUCCESS: {sender.name} - Result: {result}")

@task_failure.connect
def task_failure_handler(sender, task_id, exception, args, kwargs, traceback, einfo, **_):
    """Log when a task fails."""
    logger.error(f"TASK FAILURE: {sender.name}[{task_id}] - Exception: {exception}")
    logger.error(f"Traceback: {einfo}")

@task_revoked.connect
def task_revoked_handler(sender, request, terminated, signum, expired, **_):
    """Log when a task is revoked."""
    logger.warning(f"TASK REVOKED: {sender.name} - Terminated: {terminated}, Expired: {expired}")
''')
    
    logger.info(f"Created enhanced Celery task logging in {celery_tasks_path}")
    
    # Create a celery_init.py file to initialize the enhanced logging
    celery_init_path = "tweedhat-web/app/celery_init.py"
    
    with open(celery_init_path, 'w') as f:
        f.write('''
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
''')
    
    logger.info(f"Created enhanced Celery initialization in {celery_init_path}")
    
    # Update the __init__.py file to use the enhanced Celery initialization
    init_path = "tweedhat-web/app/__init__.py"
    
    try:
        with open(init_path, 'r') as f:
            init_content = f.read()
        
        # Check if we need to modify the file
        if "from app.celery_init import init_celery" not in init_content:
            # Replace the Celery initialization with our enhanced version
            if "celery = Celery(" in init_content:
                # Replace the Celery initialization
                init_content = init_content.replace(
                    "celery = Celery(",
                    "# Import enhanced Celery initialization\nfrom app.celery_init import init_celery\n\n# Initialize Celery\ncelery = init_celery(app)"
                )
                
                # Remove the rest of the Celery initialization
                import re
                init_content = re.sub(
                    r"celery = init_celery\(app\).*?celery\.conf\.update\(app\.config\)",
                    "celery = init_celery(app)",
                    init_content,
                    flags=re.DOTALL
                )
                
                with open(init_path, 'w') as f:
                    f.write(init_content)
                
                logger.info(f"Updated {init_path} to use enhanced Celery initialization")
            else:
                logger.warning(f"Could not find Celery initialization in {init_path}")
        else:
            logger.info(f"Enhanced Celery initialization already in {init_path}")
    except Exception as e:
        logger.error(f"Error updating {init_path}: {e}")
    
    logger.info("Enhanced job logging setup complete")

def main():
    parser = argparse.ArgumentParser(description="Enhance job logging for TweedHat")
    parser.add_argument("--apply", action="store_true", help="Apply the enhanced logging")
    
    args = parser.parse_args()
    
    print("===================================")
    print("  TweedHat Job Logging Enhancer")
    print("===================================")
    
    if args.apply:
        setup_enhanced_logging()
        print("\nEnhanced job logging has been applied.")
        print("Please restart the TweedHat application and Celery worker for changes to take effect.")
    else:
        print("\nThis script will enhance job logging for the TweedHat application.")
        print("It will create or modify the following files:")
        print("  - tweedhat-web/app/celery_tasks.py")
        print("  - tweedhat-web/app/celery_init.py")
        print("  - tweedhat-web/app/__init__.py")
        print("\nRun with --apply to apply the changes.")

if __name__ == "__main__":
    main() 