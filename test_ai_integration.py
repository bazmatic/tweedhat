#!/usr/bin/env python3
"""
Test script for AI integration module.
This script tests the AI image description functionality.
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from ai_integration import AIImageDescriber

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to test AI image description."""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test AI image description')
    parser.add_argument('--image-url', help='URL of the image to describe')
    parser.add_argument('--image-path', help='Path to the image file to describe')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Check if either image URL or path is provided
    if not args.image_url and not args.image_path:
        logger.error("Please provide either an image URL or an image path")
        parser.print_help()
        return 1
    
    try:
        # Initialize the AI image describer
        describer = AIImageDescriber()
        
        # Get the image description
        if args.image_url:
            logger.info(f"Describing image from URL: {args.image_url}")
            description = describer.describe_image(args.image_url)
        else:
            logger.info(f"Describing image from file: {args.image_path}")
            description = describer.describe_image(args.image_path)
        
        # Print the description
        print("\n--- Image Description ---")
        print(description)
        print("------------------------\n")
        
        return 0
    
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 