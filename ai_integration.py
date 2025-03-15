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

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class AIImageDescriber:
    """
    Class to describe images using AI models (Anthropic Claude or OpenAI GPT-4 Vision).
    """
    
    def __init__(self):
        """Initialize the AI image describer with the appropriate model."""
        self.ai_provider = os.getenv("AI_PROVIDER", "anthropic").lower()
        
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
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image to base64: {e}")
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
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
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
                return "Could not download the image."
            
            # Save to a temporary file
            temp_path = Path("temp_image.jpg")
            with open(temp_path, "wb") as f:
                f.write(image_data.getvalue())
            
            image_path = str(temp_path)
        else:
            image_path = image_path_or_url
        
        # Check if the file exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return "Image file not found."
        
        try:
            # Encode the image to base64
            base64_image = self._encode_image_to_base64(image_path)
            if not base64_image:
                return "Could not process the image."
            
            # Clean up temporary file if it was created
            if image_path_or_url.startswith(('http://', 'https://')) and os.path.exists(temp_path):
                os.remove(temp_path)
            
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
            
            return description
        
        except Exception as e:
            logger.error(f"Error describing image: {e}", exc_info=True)
            return f"Error describing image: {str(e)}"

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