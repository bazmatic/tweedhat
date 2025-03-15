import os
import sys
import json
import time
import logging
from datetime import datetime
from celery import shared_task

from app import celery
from app.models import Job
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(Config.BASE_DIR, "tweedhat-web.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to import the original modules
sys.path.append(os.path.dirname(Config.BASE_DIR))

# Import the original modules
try:
    from scrape import TweetScraper as TwitterScraper
    from read_tweets import TweetReader
    from ai_integration import AIImageDescriber
except ImportError as e:
    logger.error(f"Error importing original modules: {e}")
    raise


@shared_task
def scrape_tweets_task(job_id):
    """
    Task to scrape tweets from Twitter.
    
    Args:
        job_id (str): ID of the job
    """
    logger.info(f"Starting tweet scraping for job {job_id}")
    
    # Get the job
    job = Job.get_by_id(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    # Update job status
    job.update_status("scraping")
    
    try:
        # Get user settings
        user = User.get_by_id(job.user_id)
        if not user:
            job.update_status("failed", "User not found")
            return
        
        twitter_email = user.get_decrypted_setting('twitter_email')
        twitter_password = user.get_decrypted_setting('twitter_password')
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{job.target_twitter_handle}_{timestamp}.json"
        output_path = os.path.join(Config.TWEETS_DIR, output_filename)
        
        # Initialize scraper
        scraper = TwitterScraper(
            headless=True,
            debug=True,
            email=twitter_email,
            password=twitter_password
        )
        
        # Scrape tweets
        logger.info(f"Scraping tweets from {job.target_twitter_handle}")
        result = scraper.scrape_user(
            username=job.target_twitter_handle,
            max_tweets=job.max_tweets,
            output_file=output_path
        )
        
        if not result:
            job.update_status("failed", "Failed to scrape tweets")
            return
        
        # Update job with tweet file
        job.tweet_file = output_path
        job.update_status("scraped")
        
        # Start audio generation
        generate_audio_task.delay(job_id)
        
    except Exception as e:
        logger.error(f"Error scraping tweets: {e}", exc_info=True)
        job.update_status("failed", str(e))


@shared_task
def generate_audio_task(job_id):
    """
    Task to generate audio from tweets.
    
    Args:
        job_id (str): ID of the job
    """
    logger.info(f"Starting audio generation for job {job_id}")
    
    # Get the job
    job = Job.get_by_id(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    # Update job status
    job.update_status("generating_audio")
    
    try:
        # Get user settings
        user = User.get_by_id(job.user_id)
        if not user:
            job.update_status("failed", "User not found")
            return
        
        elevenlabs_api_key = user.get_decrypted_setting('elevenlabs_api_key')
        anthropic_api_key = user.get_decrypted_setting('anthropic_api_key')
        
        if not elevenlabs_api_key:
            job.update_status("failed", "ElevenLabs API key not found")
            return
        
        # Create output directory for audio files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(Config.AUDIO_DIR, f"{job.target_twitter_handle}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize tweet reader
        reader = TweetReader(
            json_file=job.tweet_file,
            api_key=elevenlabs_api_key,
            voice_id=job.voice_id,
            save_audio=True,
            output_dir=output_dir,
            describe_images=job.describe_images
        )
        
        # Load tweets
        data = reader.load_tweets()
        if not data:
            job.update_status("failed", "Failed to load tweets")
            return
        
        tweets = data.get('tweets', [])
        if not tweets:
            job.update_status("failed", "No tweets found")
            return
        
        # Process each tweet
        for i, tweet in enumerate(tweets):
            try:
                logger.info(f"Processing tweet {i+1}/{len(tweets)}")
                
                # Format the tweet for speech
                text = reader.format_tweet_for_speech(tweet)
                
                # Generate audio
                audio_data = reader.text_to_speech(text)
                if not audio_data:
                    logger.warning(f"Failed to generate audio for tweet {i+1}")
                    continue
                
                # Save audio
                tweet_id = tweet.get('id', f"unknown_{i}")
                filename = os.path.join(output_dir, f"tweet_{i}_{tweet_id}.mp3")
                
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                
                # Add audio file to job
                job.add_audio_file(filename)
                
                # Update job status
                job.update_status("processing", f"Processed {i+1}/{len(tweets)} tweets")
                
            except Exception as e:
                logger.error(f"Error processing tweet {i+1}: {e}", exc_info=True)
                # Continue with next tweet
        
        # Update job status
        job.update_status("completed")
        
    except Exception as e:
        logger.error(f"Error generating audio: {e}", exc_info=True)
        job.update_status("failed", str(e))


# Import User model here to avoid circular imports
from app.models import User 