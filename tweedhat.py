#!/usr/bin/env python3
import os
import argparse
import logging
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tweedhat.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define folder paths
TWEETS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets")
IMAGES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweet_audio")

# Create folders if they don't exist
os.makedirs(TWEETS_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def run_scraper(username, max_tweets=None, visible=False, debug=False, email=None, password=None, no_profile=False):
    """
    Run the tweet scraper to collect tweets from a user.
    
    Args:
        username (str): X.com username to scrape
        max_tweets (int): Maximum number of tweets to scrape
        visible (bool): Run in visible mode (not headless)
        debug (bool): Enable debug logging
        email (str): X.com login email
        password (str): X.com login password
        no_profile (bool): Do not use a persistent Chrome profile
        
    Returns:
        str: Path to the JSON file containing scraped tweets, or None if scraping failed
    """
    logger.info(f"Scraping tweets from {username}...")
    
    # Build the command
    cmd = ["python", "scrape.py", username]
    
    if max_tweets:
        cmd.extend(["--max", str(max_tweets)])
    
    if visible:
        cmd.append("--visible")
    
    if debug:
        cmd.append("--debug")
    
    if email:
        cmd.extend(["--email", email])
    
    if password:
        cmd.extend(["--password", password])
    
    if no_profile:
        cmd.append("--no-profile")
    
    # Run the scraper
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Extract the output file path from the log
        for line in result.stdout.split('\n'):
            if "Successfully saved tweets to" in line:
                json_file = line.split("Successfully saved tweets to")[1].strip()
                logger.info(f"Tweets saved to {json_file}")
                return json_file
        
        # If we couldn't find the output file path, look for the most recent file in the tweets folder
        logger.warning("Could not find the output file path in the scraper output")
        tweet_files = [f for f in os.listdir(TWEETS_FOLDER) if f.startswith(f"{username}_tweets_") and f.endswith(".json")]
        if tweet_files:
            # Sort by modification time, newest first
            tweet_files.sort(key=lambda x: os.path.getmtime(os.path.join(TWEETS_FOLDER, x)), reverse=True)
            json_file = os.path.join(TWEETS_FOLDER, tweet_files[0])
            logger.info(f"Using most recent tweet file: {json_file}")
            return json_file
        
        logger.error("No tweet files found for this user")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running scraper: {e}")
        logger.error(f"Scraper stderr: {e.stderr}")
        return None

def run_reader(json_file, voice_id=None, save_audio=False, output_dir=None, delay=2, max_tweets=None, debug=False, describe_images=False):
    """
    Run the tweet reader to read tweets aloud.
    
    Args:
        json_file (str): Path to the JSON file containing tweets
        voice_id (str): ID of the voice to use
        save_audio (bool): Save audio files
        output_dir (str): Directory to save audio files
        delay (int): Delay between tweets in seconds
        max_tweets (int): Maximum number of tweets to read
        debug (bool): Enable debug logging
        describe_images (bool): Use AI to describe images in tweets
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Reading tweets from {json_file}...")
    
    # If json_file doesn't include the full path and is not in the current directory,
    # check if it's in the tweets folder
    if not os.path.isabs(json_file) and not os.path.exists(json_file):
        tweets_path = os.path.join(TWEETS_FOLDER, json_file)
        if os.path.exists(tweets_path):
            json_file = tweets_path
            logger.info(f"Found tweet file in tweets folder: {json_file}")
    
    # Build the command
    cmd = ["python", "read_tweets.py", json_file]
    
    if voice_id:
        cmd.extend(["--voice-id", voice_id])
    
    if save_audio:
        cmd.append("--save-audio")
    
    if output_dir:
        cmd.extend(["--output-dir", output_dir])
    else:
        # Use the default audio folder if not specified
        cmd.extend(["--output-dir", AUDIO_FOLDER])
    
    if delay != 2:  # Only add if not the default
        cmd.extend(["--delay", str(delay)])
    
    if max_tweets:
        cmd.extend(["--max-tweets", str(max_tweets)])
    
    if debug:
        cmd.append("--debug")
    
    if describe_images:
        cmd.append("--describe-images")
    
    # Run the reader
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        logger.info("Tweet reading completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running reader: {e}")
        return False

def list_voices():
    """
    List available voices from ElevenLabs.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Listing available voices...")
    
    # Run the reader with --list-voices option
    try:
        # Use example_tweet.json as a placeholder
        subprocess.run(["python", "read_tweets.py", "example_tweet.json", "--list-voices"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error listing voices: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Scrape tweets and read them aloud using ElevenLabs voice synthesis')
    parser.add_argument('username', help='X.com username to scrape tweets from')
    
    # Scraper options
    scraper_group = parser.add_argument_group('Scraper options')
    scraper_group.add_argument('--max-tweets', type=int, help='Maximum number of tweets to scrape')
    scraper_group.add_argument('--visible', action='store_true', help='Run scraper in visible mode (not headless)')
    scraper_group.add_argument('--email', help='X.com login email')
    scraper_group.add_argument('--password', help='X.com login password')
    scraper_group.add_argument('--no-profile', action='store_true', help='Do not use a persistent Chrome profile')
    
    # Reader options
    reader_group = parser.add_argument_group('Reader options')
    reader_group.add_argument('--voice-id', help='ID of the voice to use')
    reader_group.add_argument('--save-audio', action='store_true', help='Save audio files')
    reader_group.add_argument('--output-dir', help='Directory to save audio files')
    reader_group.add_argument('--delay', type=int, default=2, help='Delay between tweets in seconds')
    reader_group.add_argument('--read-max', type=int, help='Maximum number of tweets to read')
    reader_group.add_argument('--describe-images', action='store_true', help='Use AI to describe images in tweets')
    
    # General options
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--list-voices', action='store_true', help='List available voices and exit')
    parser.add_argument('--json-file', help='Use existing JSON file instead of scraping')
    
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    # List voices if requested
    if args.list_voices:
        list_voices()
        return
    
    # Get the JSON file, either from scraping or from the argument
    json_file = args.json_file
    if not json_file:
        json_file = run_scraper(
            args.username,
            max_tweets=args.max_tweets,
            visible=args.visible,
            debug=args.debug,
            email=args.email,
            password=args.password,
            no_profile=args.no_profile
        )
        
        if not json_file:
            logger.error("Failed to scrape tweets. Exiting.")
            return
        
        # Give a moment for the file to be fully written
        time.sleep(1)
    
    # Read the tweets
    run_reader(
        json_file,
        voice_id=args.voice_id,
        save_audio=args.save_audio,
        output_dir=args.output_dir,
        delay=args.delay,
        max_tweets=args.read_max,
        debug=args.debug,
        describe_images=args.describe_images
    )

if __name__ == "__main__":
    main() 