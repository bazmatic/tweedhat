import os
import sys
import json
import time
import logging
from datetime import datetime
from celery import shared_task
from pydub import AudioSegment

from app import celery
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
    from scrape import TweetScraper
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
    logger.info(f"Job {job_id} (@{job.target_twitter_handle}): Scraping up to {job.max_tweets} tweets")
    
    try:
        # Get user settings
        user = User.get_by_id(job.user_id)
        if not user:
            error_msg = f"User {job.user_id} not found"
            logger.error(error_msg)
            job.update_status("failed", error_msg)
            return
        
        twitter_email = user.get_setting('twitter_email')
        twitter_password = user.get_setting('twitter_password')
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{job.target_twitter_handle}_{timestamp}.json"
        output_path = os.path.join(Config.TWEETS_DIR, output_filename)
        
        # Initialize scraper
        logger.info(f"Job {job_id}: Initializing TweetScraper for @{job.target_twitter_handle}")
        scraper = TweetScraper(
            username=job.target_twitter_handle,
            headless=True,
            max_tweets=job.max_tweets,
            email=twitter_email,
            password=twitter_password
        )
        
        # Scrape tweets
        logger.info(f"Job {job_id}: Starting tweet scraping for @{job.target_twitter_handle}")
        tweets = scraper.scrape_tweets()
        
        if not tweets:
            error_msg = f"No tweets found for @{job.target_twitter_handle}"
            logger.warning(f"Job {job_id}: {error_msg}")
            job.update_status("failed", error_msg)
            return
        
        # Save tweets to file
        logger.info(f"Job {job_id}: Scraped {len(tweets)} tweets from @{job.target_twitter_handle}")
        scraper.save_tweets(tweets, output_path)
        logger.info(f"Job {job_id}: Saved tweets to {output_path}")
        
        # Update job with tweet file
        job.tweet_file = output_path
        job.update_status("scraped")
        
        # Start audio generation
        logger.info(f"Job {job_id}: Queueing audio generation task")
        generate_audio_task.delay(job_id)
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = str(e)
        logger.error(f"Error scraping tweets for job {job_id}: {error_msg}\n{error_traceback}")
        job.update_status("failed", error_msg)
        
        # Make sure to close the browser if it was opened
        try:
            if 'scraper' in locals() and hasattr(scraper, 'close'):
                scraper.close()
        except Exception as close_error:
            logger.error(f"Error closing browser for job {job_id}: {close_error}")


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
            error_msg = f"User {job.user_id} not found"
            logger.error(error_msg)
            job.update_status("failed", error_msg)
            return
        
        elevenlabs_api_key = user.get_setting('elevenlabs_api_key')
        anthropic_api_key = user.get_setting('anthropic_api_key')
        
        if not elevenlabs_api_key:
            error_msg = "ElevenLabs API key not found"
            logger.error(f"Job {job_id}: {error_msg}")
            job.update_status("failed", error_msg)
            return
        
        # Create output directory for audio files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(Config.AUDIO_DIR, f"{job.target_twitter_handle}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Job {job_id}: Created output directory for audio files: {output_dir}")
        
        # Initialize tweet reader
        logger.info(f"Job {job_id}: Initializing TweetReader with voice ID: {job.voice_id}")
        reader = TweetReader(
            json_file=job.tweet_file,
            api_key=elevenlabs_api_key,
            voice_id=job.voice_id,
            save_audio=True,
            output_dir=output_dir,
            describe_images=job.describe_images
        )
        
        # Load tweets
        logger.info(f"Job {job_id}: Loading tweets from {job.tweet_file}")
        data = reader.load_tweets()
        if not data:
            error_msg = f"Failed to load tweets from {job.tweet_file}"
            logger.error(f"Job {job_id}: {error_msg}")
            job.update_status("failed", error_msg)
            return
        
        tweets = data.get('tweets', [])
        if not tweets:
            error_msg = f"No tweets found in {job.tweet_file}"
            logger.error(f"Job {job_id}: {error_msg}")
            job.update_status("failed", error_msg)
            return
        
        logger.info(f"Job {job_id}: Processing {len(tweets)} tweets for audio generation")
        
        # Process each tweet
        for i, tweet in enumerate(tweets):
            try:
                logger.info(f"Job {job_id}: Processing tweet {i+1}/{len(tweets)}")
                
                # Format the tweet for speech
                text = reader.format_tweet_for_speech(tweet)
                
                # Generate audio
                logger.info(f"Job {job_id}: Generating audio for tweet {i+1}")
                audio_data = reader.text_to_speech(text)
                if not audio_data:
                    logger.warning(f"Job {job_id}: Failed to generate audio for tweet {i+1}")
                    continue
                
                # Save audio
                tweet_id = tweet.get('id', f"unknown_{i}")
                filename = os.path.join(output_dir, f"tweet_{i}_{tweet_id}.mp3")
                
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                
                logger.info(f"Job {job_id}: Saved audio for tweet {i+1} to {filename}")
                
                # Add audio file to job
                job.add_audio_file(filename)
                
                # Update job status
                job.update_status("processing", f"Processed {i+1}/{len(tweets)} tweets")
                
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                error_msg = f"Error processing tweet {i+1}: {str(e)}"
                logger.error(f"Job {job_id}: {error_msg}\n{error_traceback}")
                # Continue with next tweet
        
        # Update job status
        logger.info(f"Job {job_id}: Completed audio generation for all tweets")
        job.update_status("completed")
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = str(e)
        logger.error(f"Error generating audio for job {job_id}: {error_msg}\n{error_traceback}")
        job.update_status("failed", error_msg)


@shared_task
def combine_audio_files_task(user_id):
    """
    Task to combine all audio files from all jobs into a single file.
    This function can be called directly or as a Celery task.
    
    Args:
        user_id (str): ID of the user
        
    Returns:
        str: Path to the combined audio file, or None if failed
    """
    logger.info(f"Starting audio file combination for user {user_id}")
    
    # Get the user
    user = User.get_by_id(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return None
    
    # Get all jobs for the user
    jobs = Job.get_by_user_id(user_id)
    
    # Collect all audio files from completed jobs
    all_audio_files = []
    for job in jobs:
        if job.status == 'completed' and job.audio_files:
            # Sort audio files by index (extracted from filename)
            sorted_files = []
            for audio_file in job.audio_files:
                filename = os.path.basename(audio_file)
                try:
                    # Extract the index from the filename (format: tweet_INDEX_ID.mp3)
                    index = int(filename.split('_')[1])
                    sorted_files.append((index, audio_file))
                except (IndexError, ValueError):
                    # If we can't extract the index, just add it to the end
                    sorted_files.append((999, audio_file))
            
            # Sort by index
            sorted_files.sort(key=lambda x: x[0])
            
            # Add to the list of all audio files
            all_audio_files.extend([file_path for _, file_path in sorted_files])
    
    if not all_audio_files:
        logger.error(f"No audio files found for user {user_id}")
        return None
    
    logger.info(f"Found {len(all_audio_files)} audio files to combine")
    
    try:
        # Create output directory for combined audio file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(Config.AUDIO_DIR, f"combined_{user_id}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Output file path
        output_file = os.path.join(output_dir, f"combined_{timestamp}.mp3")
        
        # Combine audio files
        combined = AudioSegment.empty()
        
        for i, audio_file in enumerate(all_audio_files):
            logger.info(f"Processing file {i+1}/{len(all_audio_files)}: {audio_file}")
            
            if not os.path.exists(audio_file):
                logger.warning(f"File not found: {audio_file}")
                continue
            
            try:
                # Load audio file
                audio = AudioSegment.from_mp3(audio_file)
                
                # Add a short pause between audio files (500ms)
                if i > 0:
                    combined += AudioSegment.silent(duration=500)
                
                # Append to combined audio
                combined += audio
                
                logger.info(f"Added file {i+1} to combined audio")
            except Exception as e:
                logger.error(f"Error processing audio file {audio_file}: {e}")
        
        # Export combined audio
        logger.info(f"Exporting combined audio to {output_file}")
        combined.export(output_file, format="mp3")
        
        # Update user's combined audio file
        user.set_combined_audio_file(output_file)
        
        logger.info(f"Combined audio file created successfully: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error combining audio files: {e}", exc_info=True)
        return None


# Import User model here to avoid circular imports
from app.models import User 