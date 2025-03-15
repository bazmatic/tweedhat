#!/usr/bin/env python3

import os
import sys
import uuid
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_job.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the current directory to the path
sys.path.insert(0, os.path.abspath('.'))

# Create a test job
def create_test_job():
    """Create a test job and save it to the jobs directory."""
    # Create jobs directory if it doesn't exist
    jobs_dir = os.path.join('tweedhat-web/data/jobs')
    os.makedirs(jobs_dir, exist_ok=True)
    
    # Generate a job ID
    job_id = str(uuid.uuid4())
    
    # Create job data
    job_data = {
        'job_id': job_id,
        'user_id': 'test_user',
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'target_twitter_handle': 'elonmusk',
        'max_tweets': 5,
        'describe_images': False,
        'voice_id': '21m00Tcm4TlvDq8ikWAM',  # Default voice ID
        'tweet_file': None,
        'audio_files': [],
        'error': None,
        'progress': 0,
        'progress_details': {}
    }
    
    # Save job data to file
    job_file = os.path.join(jobs_dir, f"{job_id}.json")
    with open(job_file, 'w') as f:
        json.dump(job_data, f, indent=2)
    
    logger.info(f"Created test job with ID: {job_id}")
    logger.info(f"Job file: {job_file}")
    
    return job_id

# Submit the job to Celery
def submit_job(job_id):
    """Submit the job to Celery for processing."""
    try:
        # Import the task
        from tweedhat_web.app.tasks import scrape_tweets_task
        
        # Submit the task
        result = scrape_tweets_task.delay(job_id)
        
        logger.info(f"Submitted job {job_id} to Celery")
        logger.info(f"Task ID: {result.id}")
        logger.info(f"Task status: {result.status}")
        
        return result
    except Exception as e:
        logger.error(f"Error submitting job: {e}", exc_info=True)
        return None

def main():
    """Main function."""
    print("===================================")
    print("  TweedHat Job Test")
    print("===================================")
    
    # Create a test job
    job_id = create_test_job()
    
    # Submit the job to Celery
    result = submit_job(job_id)
    
    if result:
        print(f"\nJob submitted successfully!")
        print(f"Job ID: {job_id}")
        print(f"Task ID: {result.id}")
        print(f"Task status: {result.status}")
        print("\nTo check job status, run:")
        print(f"python check_job_status.py --job-id {job_id}")
    else:
        print("\nFailed to submit job.")
        print("Check test_job.log for details.")

if __name__ == "__main__":
    main() 