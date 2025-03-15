#!/usr/bin/env python
"""
Process pending jobs script for TweedHat.
This script scans the jobs directory for pending jobs and submits them to Celery.
"""

import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tweedhat-web.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the Flask app and Celery instance
from app import celery
from app.tasks import scrape_tweets_task
from app.models import Job
from config import Config

def process_pending_jobs():
    """
    Process all pending jobs by submitting them to Celery.
    """
    logger.info("Starting to process pending jobs")
    
    # Get all job files
    jobs_dir = Config.DATA_DIR + '/jobs'
    job_files = [f for f in os.listdir(jobs_dir) if f.endswith('.json')]
    
    pending_count = 0
    
    for job_file in job_files:
        job_path = os.path.join(jobs_dir, job_file)
        
        try:
            with open(job_path, 'r') as f:
                job_data = json.load(f)
            
            # Check if job is pending
            if job_data.get('status') == 'pending':
                job_id = job_data.get('job_id')
                logger.info(f"Found pending job: {job_id}")
                
                # Submit job to Celery
                scrape_tweets_task.delay(job_id)
                
                # Update job status to 'processing'
                job = Job.get_by_id(job_id)
                if job:
                    job.status = 'processing'
                    job.updated_at = datetime.now().isoformat()
                    job.save()
                    logger.info(f"Job {job_id} submitted to Celery and status updated to 'processing'")
                    pending_count += 1
                else:
                    logger.error(f"Could not find job object for ID: {job_id}")
        
        except Exception as e:
            logger.error(f"Error processing job file {job_file}: {str(e)}")
    
    logger.info(f"Processed {pending_count} pending jobs")

if __name__ == "__main__":
    process_pending_jobs()
