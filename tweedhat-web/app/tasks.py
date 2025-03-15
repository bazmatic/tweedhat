import os
import sys
import json
import time
import logging
from datetime import datetime
from celery import shared_task, current_app as current_celery_app

# Don't import celery from app to avoid circular imports
# from app import celery
from app.models import Job, User
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


@shared_task(bind=True, name='app.tasks.scrape_tweets_task')
def scrape_tweets_task(self, job_id):
    """
    Task to scrape tweets from Twitter.
    
    Args:
        job_id (str): ID of the job
    """
    logger.info(f"Starting tweet scraping for job {job_id}")
    logger.info(f"Task ID: {self.request.id}")
    
    # Get the job
    job = Job.get_by_id(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    # Update job status
    job.update_status("scraping", progress_details={"stage": "initializing"})
    logger.info(f"Job {job_id}: Status updated to 'scraping'")
    
    try:
        # Get user settings
        user = User.get_by_id(job.user_id)
        if not user:
            logger.error(f"Job {job_id}: User {job.user_id} not found")
            job.update_status("failed", "User not found")
            return
        
        logger.info(f"Job {job_id}: Retrieved user settings for user {job.user_id}")
        twitter_email = user.get_decrypted_setting('twitter_email')
        twitter_password = user.get_decrypted_setting('twitter_password')
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{job.target_twitter_handle}_{timestamp}.json"
        output_path = os.path.join(Config.TWEETS_DIR, output_filename)
        logger.info(f"Job {job_id}: Will save tweets to {output_filename}")
        
        # Initialize scraper
        logger.info(f"Job {job_id}: Initializing Twitter scraper")
        job.update_status("scraping", progress_details={"stage": "initializing_scraper"})
        scraper = TwitterScraper(
            headless=True,
            debug=True,
            email=twitter_email,
            password=twitter_password
        )
        
        # Set up a callback to track scraping progress
        def progress_callback(current, total):
            logger.info(f"Job {job_id}: Scraping progress - {current}/{total} tweets")
            job.update_progress(current, total, stage="scraping")
        
        # Scrape tweets
        logger.info(f"Job {job_id}: Starting to scrape tweets from @{job.target_twitter_handle} (max: {job.max_tweets})")
        job.update_status("scraping", progress_details={"stage": "scraping_tweets"})
        
        # Add progress callback if supported by the scraper
        scraper_kwargs = {}
        if hasattr(scraper, 'set_progress_callback'):
            scraper.set_progress_callback(progress_callback)
        elif 'progress_callback' in scraper.scrape_user.__code__.co_varnames:
            scraper_kwargs['progress_callback'] = progress_callback
        
        result = scraper.scrape_user(
            username=job.target_twitter_handle,
            max_tweets=job.max_tweets,
            output_file=output_path,
            **scraper_kwargs
        )
        
        if not result:
            logger.error(f"Job {job_id}: Failed to scrape tweets from @{job.target_twitter_handle}")
            job.update_status("failed", "Failed to scrape tweets")
            return
        
        # Check how many tweets were scraped
        try:
            with open(output_path, 'r') as f:
                tweet_data = json.load(f)
                tweet_count = len(tweet_data.get('tweets', []))
                logger.info(f"Job {job_id}: Successfully scraped {tweet_count} tweets from @{job.target_twitter_handle}")
                job.update_status("scraped", progress_details={
                    "tweet_count": tweet_count,
                    "stage": "scraping_completed"
                })
        except Exception as e:
            logger.warning(f"Job {job_id}: Could not count tweets: {e}")
            job.update_status("scraped")
        
        # Update job with tweet file
        job.tweet_file = output_path
        logger.info(f"Job {job_id}: Status updated to 'scraped'")
        
        # Start audio generation
        logger.info(f"Job {job_id}: Queueing audio generation task")
        generate_audio_task.delay(job_id)
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error scraping tweets: {e}", exc_info=True)
        job.update_status("failed", str(e))


@shared_task(bind=True, name='app.tasks.generate_audio_task')
def generate_audio_task(self, job_id):
    """
    Task to generate audio from tweets.
    
    Args:
        job_id (str): ID of the job
    """
    logger.info(f"Starting audio generation for job {job_id}")
    logger.info(f"Task ID: {self.request.id}")
    
    # Get the job
    job = Job.get_by_id(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    # Update job status
    job.update_status("generating_audio", progress_details={"stage": "initializing"})
    logger.info(f"Job {job_id}: Status updated to 'generating_audio'")
    
    try:
        # Get user settings
        user = User.get_by_id(job.user_id)
        if not user:
            logger.error(f"Job {job_id}: User {job.user_id} not found")
            job.update_status("failed", "User not found")
            return
        
        logger.info(f"Job {job_id}: Retrieved user settings for user {job.user_id}")
        elevenlabs_api_key = user.get_decrypted_setting('elevenlabs_api_key')
        anthropic_api_key = user.get_decrypted_setting('anthropic_api_key')
        
        if not elevenlabs_api_key:
            logger.error(f"Job {job_id}: ElevenLabs API key not found")
            job.update_status("failed", "ElevenLabs API key not found")
            return
        
        # Create output directory for audio files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(Config.AUDIO_DIR, f"{job.target_twitter_handle}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Job {job_id}: Created output directory for audio files: {output_dir}")
        
        # Initialize tweet reader
        logger.info(f"Job {job_id}: Initializing TweetReader with voice_id={job.voice_id}, describe_images={job.describe_images}")
        job.update_status("generating_audio", progress_details={"stage": "initializing_reader"})
        reader = TweetReader(
            json_file=job.tweet_file,
            api_key=elevenlabs_api_key,
            voice_id=job.voice_id,
            save_audio=True,
            output_dir=output_dir,
            describe_images=job.describe_images
        )
        
        # Set Anthropic API key if image description is enabled
        if job.describe_images and anthropic_api_key:
            logger.info(f"Job {job_id}: Setting up AI image description with Anthropic")
            os.environ['ANTHROPIC_API_KEY'] = anthropic_api_key
        
        # Load tweets
        logger.info(f"Job {job_id}: Loading tweets from {job.tweet_file}")
        job.update_status("generating_audio", progress_details={"stage": "loading_tweets"})
        data = reader.load_tweets()
        if not data:
            logger.error(f"Job {job_id}: Failed to load tweets from {job.tweet_file}")
            job.update_status("failed", "Failed to load tweets")
            return
        
        tweets = data.get('tweets', [])
        if not tweets:
            logger.error(f"Job {job_id}: No tweets found in {job.tweet_file}")
            job.update_status("failed", "No tweets found")
            return
        
        logger.info(f"Job {job_id}: Loaded {len(tweets)} tweets for processing")
        job.update_status("processing", progress_details={
            "stage": "processing_tweets",
            "total_tweets": len(tweets)
        })
        
        # Process each tweet
        for i, tweet in enumerate(tweets):
            try:
                logger.info(f"Job {job_id}: Processing tweet {i+1}/{len(tweets)} - ID: {tweet.get('id', 'unknown')}")
                
                # Update progress
                job.update_progress(i+1, len(tweets), stage="processing")
                
                # Check if tweet has images
                has_images = any(media.get('type') == 'photo' for media in tweet.get('media', []))
                if has_images and job.describe_images:
                    logger.info(f"Job {job_id}: Tweet {i+1} has images that will be described")
                    job.update_status(job.status, progress_details={
                        "current_tweet": i+1,
                        "current_tweet_has_images": True
                    })
                
                # Format the tweet for speech
                text = reader.format_tweet_for_speech(tweet)
                logger.info(f"Job {job_id}: Formatted tweet {i+1} for speech (text length: {len(text)})")
                
                # Generate audio
                logger.info(f"Job {job_id}: Generating audio for tweet {i+1}")
                job.update_status(job.status, progress_details={
                    "current_tweet": i+1,
                    "current_action": "generating_audio"
                })
                
                start_time = time.time()
                audio_data = reader.text_to_speech(text)
                elapsed_time = time.time() - start_time
                
                if not audio_data:
                    logger.warning(f"Job {job_id}: Failed to generate audio for tweet {i+1}")
                    job.update_status(job.status, progress_details={
                        "current_tweet": i+1,
                        "current_action": "failed_audio_generation"
                    })
                    continue
                
                logger.info(f"Job {job_id}: Generated audio for tweet {i+1} in {elapsed_time:.2f} seconds")
                
                # Save audio
                tweet_id = tweet.get('id', f"unknown_{i}")
                filename = os.path.join(output_dir, f"tweet_{i}_{tweet_id}.mp3")
                
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                
                logger.info(f"Job {job_id}: Saved audio for tweet {i+1} to {filename}")
                
                # Add audio file to job
                job.add_audio_file(filename)
                logger.info(f"Job {job_id}: Added audio file to job record")
                
                # Update job status with progress
                progress_message = f"Processed {i+1}/{len(tweets)} tweets"
                job.update_status("processing", progress_message, progress_details={
                    "current_tweet": i+1,
                    "total_tweets": len(tweets),
                    "percentage_complete": round((i+1) / len(tweets) * 100, 2)
                })
                logger.info(f"Job {job_id}: {progress_message}")
                
            except Exception as e:
                logger.error(f"Job {job_id}: Error processing tweet {i+1}: {e}", exc_info=True)
                job.update_status(job.status, progress_details={
                    "current_tweet": i+1,
                    "error": str(e)
                })
                # Continue with next tweet
        
        # Update job status
        job.update_status("completed", progress_details={
            "stage": "completed",
            "total_audio_files": len(job.audio_files)
        })
        logger.info(f"Job {job_id}: All tweets processed. Status updated to 'completed'")
        
    except Exception as e:
        logger.error(f"Job {job_id}: Error generating audio: {e}", exc_info=True)
        job.update_status("failed", str(e))


# Import User model here to avoid circular imports
from app.models import User 