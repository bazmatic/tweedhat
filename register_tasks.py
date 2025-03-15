#!/usr/bin/env python3

import os
import sys
import logging
from celery import Celery

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def register_tasks():
    """Register tasks with Celery."""
    # Create Celery app
    celery = Celery(
        'tweedhat',
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
        worker_hijack_root_logger=False,
        worker_redirect_stdouts=False,
        task_track_started=True,
        task_send_sent_event=True,
        worker_send_task_events=True,
        task_acks_late=True,
    )
    
    # Define tasks
    @celery.task(name='app.tasks.scrape_tweets_task', bind=True)
    def scrape_tweets_task(self, job_id):
        """Task to scrape tweets from Twitter."""
        logger.info(f"Starting tweet scraping for job {job_id}")
        logger.info(f"Task ID: {self.request.id}")
        return f"Scraping tweets for job {job_id}"
    
    @celery.task(name='app.tasks.generate_audio_task', bind=True)
    def generate_audio_task(self, job_id):
        """Task to generate audio from tweets."""
        logger.info(f"Starting audio generation for job {job_id}")
        logger.info(f"Task ID: {self.request.id}")
        return f"Generating audio for job {job_id}"
    
    # Print registered tasks
    logger.info("Registered tasks:")
    for task_name in sorted(celery.tasks.keys()):
        if not task_name.startswith('celery.'):
            logger.info(f"- {task_name}")
    
    return celery

def main():
    """Main function."""
    print("===================================")
    print("  TweedHat Task Registration")
    print("===================================")
    
    # Register tasks
    celery = register_tasks()
    
    print("\nTasks registered successfully!")
    print("You can now start the Celery worker with:")
    print("  ./start_celery_debug.sh")

if __name__ == "__main__":
    main() 