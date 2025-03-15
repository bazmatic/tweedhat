#!/usr/bin/env python3
import os
import base64
import logging
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
import hashlib

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class AIImageDescriber:
    """
    Class to describe images using AI models (Anthropic Claude or OpenAI GPT-4 Vision).
    """
    
    def __init__(self, images_folder=None):
        """
        Initialize the AI image describer with the appropriate model.
        
        Args:
            images_folder (str, optional): Path to folder for storing downloaded images
        """
        self.ai_provider = os.getenv("AI_PROVIDER", "anthropic").lower()
        self.images_folder = images_folder or os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
        
        # Create images folder if it doesn't exist
        os.makedirs(self.images_folder, exist_ok=True)
        logger.info(f"Using images folder: {self.images_folder}")
        
        if self.ai_provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            self.model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
            if not self.api_key:
                logger.error("Anthropic API key not found in environment variables")
                raise ValueError("Anthropic API key is required")
            
            self.client = ChatAnthropic(
                anthropic_api_key=self.api_key,
                model=self.model_name
            )
            logger.info(f"Using Anthropic {self.model_name} for image description")
            
        elif self.ai_provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.model_name = os.getenv("OPENAI_MODEL", "gpt-4-vision-preview")
            if not self.api_key:
                logger.error("OpenAI API key not found in environment variables")
                raise ValueError("OpenAI API key is required")
            
            self.client = ChatOpenAI(
                api_key=self.api_key,
                model=self.model_name
            )
            logger.info(f"Using OpenAI {self.model_name} for image description")
            
        else:
            logger.error(f"Unsupported AI provider: {self.ai_provider}")
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}. Use 'anthropic' or 'openai'")
    
    def _encode_image_to_base64(self, image_path):
        """
        Encode an image to base64.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Base64-encoded image
        """
        try:
            # Check file size
            file_size = os.path.getsize(image_path)
            if file_size > 5 * 1024 * 1024:  # 5MB
                logger.info(f"Image is too large ({file_size / (1024 * 1024):.2f} MB), resizing")
                return self._resize_and_encode_image(image_path)
            
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image to base64: {e}")
            return None
    
    def _resize_and_encode_image(self, image_path):
        """
        Resize an image to reduce its file size and encode it to base64.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Base64-encoded resized image
        """
        try:
            # Open the image
            with Image.open(image_path) as img:
                # Calculate new dimensions while maintaining aspect ratio
                width, height = img.size
                max_dimension = 1500  # Max dimension for either width or height
                
                if width > height and width > max_dimension:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                elif height > max_dimension:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                else:
                    # If the image is already small enough, just reduce quality
                    new_width, new_height = width, height
                
                # Resize the image
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Save to a BytesIO object with reduced quality
                buffer = BytesIO()
                if resized_img.mode == 'RGBA':
                    resized_img = resized_img.convert('RGB')
                resized_img.save(buffer, format="JPEG", quality=85)
                buffer.seek(0)
                
                # Check if the resized image is still too large
                if buffer.getbuffer().nbytes > 5 * 1024 * 1024:
                    # Try again with even lower quality
                    buffer = BytesIO()
                    resized_img.save(buffer, format="JPEG", quality=65)
                    buffer.seek(0)
                
                # Encode to base64
                encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                logger.info(f"Image resized from {width}x{height} to {new_width}x{new_height}")
                return encoded
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            return None
    
    def _download_image(self, image_url):
        """
        Download an image from a URL.
        
        Args:
            image_url (str): URL of the image
            
        Returns:
            BytesIO: Image data
        """
        try:
            # Add user agent and headers to avoid being blocked
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://nitter.net/"
            }
            
            # Handle URL encoding issues
            if '%' in image_url:
                # URL might be double-encoded
                try:
                    from urllib.parse import unquote
                    decoded_url = unquote(image_url)
                    logger.debug(f"Decoded URL: {decoded_url}")
                    image_url = decoded_url
                except Exception as e:
                    logger.warning(f"Error decoding URL: {e}")
            
            # Special handling for Nitter URLs
            if 'nitter.net' in image_url:
                # Try different Nitter URL formats
                original_url = image_url
                
                # For video previews, try alternative formats
                if 'card_img' in image_url:
                    # Extract the tweet ID and image ID from the URL
                    import re
                    tweet_id_match = re.search(r'/(\d+)/', image_url)
                    image_id_match = re.search(r'/([A-Za-z0-9_-]+)\?', image_url)
                    
                    if tweet_id_match and image_id_match:
                        tweet_id = tweet_id_match.group(1)
                        image_id = image_id_match.group(1)
                        
                        # Try alternative URL formats
                        alternative_urls = [
                            f"https://nitter.net/pic/media%2F{image_id}%3Fformat%3Djpg%26name%3Dsmall",
                            f"https://nitter.net/pic/media%2F{image_id}.jpg",
                            f"https://nitter.net/pic/orig/media%2F{image_id}.jpg",
                            f"https://nitter.net/pic/{tweet_id}/media%2F{image_id}.jpg"
                        ]
                        
                        for alt_url in alternative_urls:
                            logger.debug(f"Trying alternative Nitter URL: {alt_url}")
                            try:
                                response = requests.get(alt_url, stream=True, headers=headers, timeout=10)
                                if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image/'):
                                    logger.info(f"Successfully downloaded image from alternative URL: {alt_url}")
                                    return BytesIO(response.content)
                            except Exception as e:
                                logger.debug(f"Failed to download from alternative URL {alt_url}: {e}")
                                continue
                
                # If we couldn't find an alternative URL, try the original
                image_url = original_url
            
            logger.debug(f"Downloading image from: {image_url}")
            response = requests.get(image_url, stream=True, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            logger.debug(f"Image content type: {content_type}")
            
            # Verify that we actually got an image
            if not content_type.startswith('image/'):
                logger.warning(f"Downloaded content is not an image: {content_type}")
                # If it's HTML, it might be an error page
                if content_type.startswith('text/html'):
                    logger.debug("Received HTML instead of an image, likely an error page")
                    raise ValueError(f"Received HTML instead of an image from {image_url}")
            
            return BytesIO(response.content)
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {e}")
            return None
    
    def describe_image(self, image_path_or_url, prompt=None):
        """
        Generate a description of an image using AI.
        
        Args:
            image_path_or_url (str): Path to the image file or URL
            prompt (str, optional): Custom prompt for the AI
            
        Returns:
            str: Description of the image
        """
        # Default prompt if none provided
        if not prompt:
            prompt = "Describe this image in detail, focusing on the main subjects and any text visible in the image."
        
        # Check if the input is a URL or a local file path
        if image_path_or_url.startswith(('http://', 'https://')):
            logger.info(f"Downloading image from URL: {image_path_or_url}")
            image_data = self._download_image(image_path_or_url)
            if not image_data:
                return "Error: Image unavailable."
            
            # Generate a filename based on the URL
            url_hash = hashlib.md5(image_path_or_url.encode()).hexdigest()
            filename = f"image_{url_hash}.jpg"
            temp_path = os.path.join(self.images_folder, filename)
            
            # Save to the images folder
            try:
                # Try to open and validate the image data before saving
                try:
                    img = Image.open(image_data)
                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    # Save as JPEG
                    img.save(temp_path, format="JPEG", quality=95)
                    logger.info(f"Saved and converted image to {temp_path}")
                except Exception as e:
                    logger.error(f"Error processing downloaded image: {e}")
                    # Try direct save as fallback
                    image_data.seek(0)
                    with open(temp_path, "wb") as f:
                        f.write(image_data.getvalue())
                    logger.info(f"Saved raw image data to {temp_path}")
            except Exception as e:
                logger.error(f"Failed to save image: {e}")
                return "Error: Image unavailable."
            
            image_path = temp_path
        else:
            # If it's a relative path and not in the current directory, check if it's in the images folder
            if not os.path.isabs(image_path_or_url) and not os.path.exists(image_path_or_url):
                images_path = os.path.join(self.images_folder, image_path_or_url)
                if os.path.exists(images_path):
                    image_path = images_path
                    logger.info(f"Found image in images folder: {image_path}")
                else:
                    image_path = image_path_or_url
            else:
                image_path = image_path_or_url
        
        # Check if the file exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return "Error: Image unavailable."
        
        try:
            # Ensure the image is in a format that the AI can process
            temp_converted_path = None
            try:
                # Open and convert the image to ensure it's in a valid format
                with Image.open(image_path) as img:
                    # Check if the image is valid
                    img.verify()
                    logger.debug(f"Image verified: {image_path}")
                
                # Reopen the image after verification
                with Image.open(image_path) as img:
                    # Convert to RGB if it's not already
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save to a temporary file with a controlled format
                    temp_converted_path = f"{image_path}_converted.jpg"
                    img.save(temp_converted_path, format="JPEG", quality=95)
                    
                    # Use the converted image
                    image_path = temp_converted_path
                    logger.debug(f"Converted image saved to {image_path}")
            except Exception as e:
                logger.warning(f"Error converting image: {e}")
                # Continue with the original image if conversion fails
            
            # Encode the image to base64
            base64_image = self._encode_image_to_base64(image_path)
            if not base64_image:
                return "Could not process the image."
            
            # Create the message based on the AI provider
            if self.ai_provider == "anthropic":
                system_message = SystemMessage(content="You are an expert at describing images in detail.")
                human_message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                )
                messages = [system_message, human_message]
            else:  # OpenAI
                human_message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                )
                messages = [human_message]
            
            # Get the response from the AI
            logger.info("Sending image to AI for description")
            response = self.client.invoke(messages)
            
            # Extract the description
            description = response.content
            logger.info("Received image description from AI")
            
            # Clean up temporary converted file if it exists
            if temp_converted_path and os.path.exists(temp_converted_path):
                try:
                    os.remove(temp_converted_path)
                except Exception:
                    pass
            
            return description
        
        except Exception as e:
            logger.error(f"Error describing image: {e}", exc_info=True)
            return "Error: Image unavailable."

# Example usage
if __name__ == "__main__":
    # Set up logging for standalone use
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Describe an image using AI')
    parser.add_argument('image_path', help='Path to the image file or URL')
    args = parser.parse_args()
    
    # Initialize the AI image describer
    describer = AIImageDescriber()
    
    # Describe the image
    description = describer.describe_image(args.image_path)
    
    # Print the description
    print("\nImage Description:")
    print("-----------------")
    print(description) 