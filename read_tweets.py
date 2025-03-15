#!/usr/bin/env python3
import json
import os
import argparse
import time
import logging
import requests
import io
import subprocess
import platform
import tempfile
from pathlib import Path
from datetime import datetime
from mutagen.mp3 import MP3
import re
from dotenv import load_dotenv

# Import AI image describer
try:
    from ai_integration import AIImageDescriber
    AI_INTEGRATION_AVAILABLE = True
except ImportError:
    AI_INTEGRATION_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("AI integration module not available. Image description will be disabled.")

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tweet_reader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get ElevenLabs API key from environment variable
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Define folder paths
TWEETS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets")
IMAGES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweet_audio")

# Create folders if they don't exist
os.makedirs(TWEETS_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

class TweetReader:
    def __init__(self, json_file, api_key=None, voice_id="21m00Tcm4TlvDq8ikWAM", save_audio=False, output_dir=None, describe_images=False):
        """
        Initialize the TweetReader.
        
        Args:
            json_file (str): Path to the JSON file containing tweets
            api_key (str): ElevenLabs API key
            voice_id (str): ID of the voice to use (default is "Rachel")
            save_audio (bool): Whether to save audio files
            output_dir (str): Directory to save audio files
            describe_images (bool): Whether to use AI to describe images in tweets
        """
        # If json_file doesn't include the full path and is not in the current directory,
        # check if it's in the tweets folder
        if not os.path.isabs(json_file) and not os.path.exists(json_file):
            tweets_path = os.path.join(TWEETS_FOLDER, json_file)
            if os.path.exists(tweets_path):
                self.json_file = tweets_path
                logger.info(f"Found tweet file in tweets folder: {tweets_path}")
            else:
                self.json_file = json_file
        else:
            self.json_file = json_file
            
        self.api_key = api_key or ELEVENLABS_API_KEY  # Use environment variable if none provided
        self.voice_id = voice_id
        self.save_audio = save_audio
        self.api_url = "https://api.elevenlabs.io/v1"
        self.describe_images = describe_images
        
        # Initialize AI image describer if enabled
        if self.describe_images:
            if AI_INTEGRATION_AVAILABLE:
                try:
                    self.image_describer = AIImageDescriber(images_folder=IMAGES_FOLDER)
                    logger.info("AI image description enabled")
                except Exception as e:
                    logger.error(f"Error initializing AI image describer: {e}")
                    self.describe_images = False
                    self.image_describer = None
            else:
                logger.warning("AI integration not available. Image description disabled.")
                self.describe_images = False
                self.image_describer = None
        else:
            self.image_describer = None
        
        # Set up output directory
        if save_audio:
            if output_dir:
                self.output_dir = Path(output_dir)
            else:
                self.output_dir = Path(AUDIO_FOLDER)
            
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Audio files will be saved to {self.output_dir}")
        
        logger.info(f"Initializing TweetReader for file: {self.json_file}")
        logger.info(f"Using voice ID: {voice_id}")
        logger.info(f"Save audio: {save_audio}")
        
        # Validate API key
        if not self.api_key:
            logger.warning("No API key provided. Please provide an API key.")
            raise ValueError("API key is required")
        
        # Check if we can use a better audio player
        try:
            import pygame
            self.use_pygame = True
            pygame.mixer.init()
            logger.info("Using pygame for audio playback")
        except ImportError:
            self.use_pygame = False
            logger.info("Pygame not available, using system default player")
    
    def load_tweets(self):
        """
        Load tweets from the JSON file.
        
        Returns:
            dict: The loaded JSON data
        """
        logger.info(f"Loading tweets from {self.json_file}")
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded {data.get('tweet_count', 0)} tweets from {data.get('username', 'unknown')}")
            return data
        except Exception as e:
            logger.error(f"Error loading tweets: {e}", exc_info=True)
            return None
    
    def list_available_voices(self):
        """
        List all available voices from ElevenLabs.
        """
        try:
            headers = {
                "xi-api-key": self.api_key
            }
            response = requests.get(f"{self.api_url}/voices", headers=headers)
            response.raise_for_status()
            
            voices_data = response.json()
            voices = voices_data.get("voices", [])
            
            logger.info("Available voices:")
            for voice in voices:
                logger.info(f"- {voice.get('name')} (ID: {voice.get('voice_id')})")
            
            return voices
        except Exception as e:
            logger.error(f"Error listing voices: {e}", exc_info=True)
            return []
    
    def format_tweet_for_speech(self, tweet):
        """
        Format a tweet for speech synthesis.
        
        Args:
            tweet (dict): Tweet data
            
        Returns:
            str: Formatted text for speech synthesis
        """
        text = tweet.get('text', '')
        timestamp = tweet.get('timestamp', '')
        has_video = tweet.get('has_video', False)
        has_media = tweet.get('has_media', False)
        
        # Get media links from either 'media_links' or 'media' field
        media_links = tweet.get('media_links', [])
        if not media_links and 'media' in tweet:
            media_links = tweet.get('media', [])
        
        # Check for video-related text patterns
        video_patterns = [
            r'piped\S*',
            r'youtube\S*',
            r'youtu\.be\S*',
            r'vimeo\S*',
            r'video\S*',
            r'watch\?v=\S*'
        ]
        
        has_video_text = False
        for pattern in video_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                has_video_text = True
                # Remove the video-related text
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Replace URLs with "there is a link" instead of reading them out
        text = re.sub(r'https?://\S+', ' there is a link ', text)
        
        # Format hashtags for better reading
        text = text.replace('#', ' hashtag ')
        
        # Format mentions for better reading
        text = text.replace('@', ' at ')
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Convert timestamp to "days ago" format if available
        if timestamp:
            time_ago = self._convert_timestamp_to_time_ago(timestamp)
            formatted_text = f"Tweet from {time_ago}: {text}"
        else:
            formatted_text = text
        
        # Add information about video if present
        if has_video or has_video_text or has_media and "video" in text.lower():
            formatted_text += " There is a video in this tweet."
        
        # Add AI description of images if enabled and media links are available
        if self.describe_images and self.image_describer and media_links:
            # First, check for video previews
            video_previews = [link for link in media_links if link.startswith("video_preview:")]
            regular_images = [link for link in media_links if not link.startswith("video_preview:")]
            
            # Process video previews
            for i, preview_link in enumerate(video_previews):
                # Extract the actual URL from the prefixed string
                actual_url = preview_link.split("video_preview:", 1)[1]
                try:
                    logger.info(f"Describing video preview image: {actual_url}")
                    description = self.image_describer.describe_image(
                        actual_url, 
                        prompt="This is a preview frame from a video in a tweet. Describe what you see in this frame and what the video might be about."
                    )
                    if description and not description.startswith("Error"):
                        # Add the video description to the formatted text
                        if len(video_previews) > 1:
                            formatted_text += f" Video {i+1} appears to show: {description}"
                        else:
                            formatted_text += f" The video appears to show: {description}"
                except Exception as e:
                    logger.error(f"Error describing video preview: {e}")
            
            # Process regular images
            for i, media_link in enumerate(regular_images):
                # Check if it's an image (simple check based on extension)
                if any(media_link.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    try:
                        logger.info(f"Describing image: {media_link}")
                        description = self.image_describer.describe_image(media_link)
                        if description and not description.startswith("Error"):
                            # Add the image description to the formatted text
                            if len(regular_images) > 1:
                                formatted_text += f" Image {i+1}: {description}"
                            else:
                                formatted_text += f" The image shows: {description}"
                    except Exception as e:
                        logger.error(f"Error describing image: {e}")
        
        return formatted_text
    
    def _convert_timestamp_to_time_ago(self, timestamp):
        """
        Convert a timestamp string to a "time ago" format.
        
        Args:
            timestamp (str): Timestamp string (e.g., "Jun 10, 2024 · 10:18 PM UTC")
            
        Returns:
            str: Time ago string (e.g., "2 days ago")
        """
        try:
            # Extract the date part from the timestamp
            # Example format: "Jun 10, 2024 · 10:18 PM UTC"
            date_match = re.match(r'([A-Za-z]+ \d+, \d{4})', timestamp)
            if not date_match:
                return timestamp
            
            date_str = date_match.group(1)
            
            # Parse the date
            tweet_date = datetime.strptime(date_str, '%b %d, %Y')
            
            # Calculate days difference
            now = datetime.now()
            delta = now - tweet_date
            days = delta.days
            
            # Format the time ago string
            if days == 0:
                return "today"
            elif days == 1:
                return "yesterday"
            else:
                return f"{days} days ago"
        except Exception as e:
            logger.error(f"Error converting timestamp: {e}", exc_info=True)
            return timestamp
    
    def text_to_speech(self, text):
        """
        Convert text to speech using ElevenLabs API.
        
        Args:
            text (str): Text to convert to speech
            
        Returns:
            bytes: Audio data
        """
        try:
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(
                f"{self.api_url}/text-to-speech/{self.voice_id}",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            
            return response.content
        except Exception as e:
            logger.error(f"Error converting text to speech: {e}", exc_info=True)
            return None
    
    def get_audio_duration(self, audio_data):
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_data (bytes): Audio data
            
        Returns:
            float: Duration in seconds
        """
        try:
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Get duration using mutagen
            audio = MP3(temp_path)
            duration = audio.info.length
            
            # Clean up
            os.unlink(temp_path)
            
            return duration
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}", exc_info=True)
            return 5.0  # Default to 5 seconds if we can't determine
    
    def play_audio(self, audio_data):
        """
        Play audio data and wait for it to finish.
        
        Args:
            audio_data (bytes): Audio data to play
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Get audio duration
            duration = self.get_audio_duration(audio_data)
            logger.info(f"Audio duration: {duration:.2f} seconds")
            
            # Play the audio
            if self.use_pygame:
                try:
                    import pygame
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    
                    # Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    
                    # Add a small pause after playback
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error playing audio with pygame: {e}")
                    # Fall back to system player
                    self._play_with_system(temp_path, duration)
            else:
                # Use system player
                self._play_with_system(temp_path, duration)
            
            # Clean up
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            
            return True
        except Exception as e:
            logger.error(f"Error playing audio: {e}", exc_info=True)
            return False
    
    def _play_with_system(self, file_path, duration):
        """
        Play audio with system player and wait for it to finish.
        
        Args:
            file_path (str): Path to audio file
            duration (float): Duration in seconds
        """
        system = platform.system()
        
        try:
            if system == 'Darwin':  # macOS
                subprocess.Popen(['afplay', file_path])
            elif system == 'Windows':
                os.startfile(file_path)
            else:  # Linux
                subprocess.Popen(['xdg-open', file_path])
            
            # Wait for the audio to finish playing
            # Add a small buffer to ensure it completes
            time.sleep(duration + 1.0)
        except Exception as e:
            logger.error(f"Error playing with system player: {e}")
            # If system player fails, just wait the duration
            time.sleep(duration + 1.0)
    
    def read_tweet(self, tweet, index=None):
        """
        Read a tweet aloud using ElevenLabs.
        
        Args:
            tweet (dict): Tweet data
            index (int, optional): Index of the tweet
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format the tweet for speech
            text = self.format_tweet_for_speech(tweet)
            logger.info(f"Reading tweet {index+1 if index is not None else '?'}: {text[:50]}...")
            
            # Generate audio
            audio_data = self.text_to_speech(text)
            if not audio_data:
                logger.error("Failed to generate audio")
                return False
            
            # Save audio if requested
            if self.save_audio:
                tweet_id = tweet.get('id', 'unknown')
                if index is not None:
                    filename = self.output_dir / f"tweet_{index}_{tweet_id}.mp3"
                else:
                    filename = self.output_dir / f"tweet_{tweet_id}.mp3"
                
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                logger.info(f"Saved audio to {filename}")
            
            # Play the audio and wait for it to finish
            return self.play_audio(audio_data)
        except Exception as e:
            logger.error(f"Error reading tweet: {e}", exc_info=True)
            return False
    
    def read_all_tweets(self, delay=2, max_tweets=None):
        """
        Read all tweets aloud.
        
        Args:
            delay (int): Delay between tweets in seconds
            max_tweets (int, optional): Maximum number of tweets to read
            
        Returns:
            int: Number of tweets read
        """
        data = self.load_tweets()
        if not data:
            logger.error("No tweets to read")
            return 0
        
        tweets = data.get('tweets', [])
        username = data.get('username', 'unknown')
        
        if not tweets:
            logger.warning("No tweets found in the data")
            return 0
        
        # Apply max_tweets limit if specified
        if max_tweets is not None and max_tweets > 0:
            tweets = tweets[:max_tweets]
            logger.info(f"Limiting to {max_tweets} tweets")
        
        logger.info(f"Reading {len(tweets)} tweets from {username}")
        
        # Introduce the tweets
        intro_text = f"Reading {len(tweets)} tweets from {username}."
        intro_audio = self.text_to_speech(intro_text)
        if intro_audio:
            self.play_audio(intro_audio)
        
        # Read each tweet
        tweets_read = 0
        for i, tweet in enumerate(tweets):
            success = self.read_tweet(tweet, i)
            if success:
                tweets_read += 1
                
                # Add a delay between tweets
                if i < len(tweets) - 1:
                    time.sleep(delay)
        
        # Conclude the reading
        outro_text = f"That was {tweets_read} tweets from {username}."
        outro_audio = self.text_to_speech(outro_text)
        if outro_audio:
            self.play_audio(outro_audio)
        
        logger.info(f"Finished reading {tweets_read} tweets")
        return tweets_read

def parse_args():
    parser = argparse.ArgumentParser(description='Read tweets using ElevenLabs API')
    parser.add_argument('json_file', help='JSON file containing tweets')
    parser.add_argument('--api-key', help='ElevenLabs API key')
    parser.add_argument('--voice-id', help='Voice ID to use')
    parser.add_argument('--list-voices', action='store_true', help='List available voices')
    parser.add_argument('--save-audio', action='store_true', help='Save audio files')
    parser.add_argument('--output-dir', default='tweet_audio', help='Directory to save audio files')
    parser.add_argument('--max-tweets', type=int, help='Maximum number of tweets to read')
    parser.add_argument('--delay', type=int, default=0, help='Delay between tweets in seconds')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--describe-images', action='store_true', help='Use AI to describe images in tweets')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Get API key
    api_key = args.api_key or os.getenv('ELEVENLABS_API_KEY') or "YOUR_API_KEY_HERE"
    
    # Initialize tweet reader
    reader = TweetReader(
        json_file=args.json_file,
        api_key=api_key,
        voice_id=args.voice_id,
        save_audio=args.save_audio,
        output_dir=args.output_dir,
        describe_images=args.describe_images
    )
    
    # List voices if requested
    if args.list_voices:
        reader.list_available_voices()
        return
    
    # Read all tweets
    reader.read_all_tweets(delay=args.delay, max_tweets=args.max_tweets)

if __name__ == "__main__":
    main() 