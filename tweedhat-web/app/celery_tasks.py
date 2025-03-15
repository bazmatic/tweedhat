
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
