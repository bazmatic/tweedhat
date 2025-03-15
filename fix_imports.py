#!/usr/bin/env python3

import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_symlink():
    """Create a symbolic link to fix the module import issue."""
    # Get the current directory
    current_dir = os.path.abspath('.')
    
    # Check if the tweedhat-web directory exists
    if not os.path.exists('tweedhat-web'):
        logger.error("tweedhat-web directory not found")
        return False
    
    # Create a symbolic link from tweedhat_web to tweedhat-web
    if not os.path.exists('tweedhat_web'):
        try:
            os.symlink('tweedhat-web', 'tweedhat_web')
            logger.info("Created symbolic link from tweedhat_web to tweedhat-web")
            return True
        except Exception as e:
            logger.error(f"Error creating symbolic link: {e}")
            return False
    else:
        logger.info("tweedhat_web already exists")
        return True

def main():
    """Main function."""
    print("===================================")
    print("  TweedHat Import Fix")
    print("===================================")
    
    # Create the symbolic link
    if create_symlink():
        print("\nImport fix applied successfully!")
        print("You can now run the application with:")
        print("  ./start_tweedhat.sh")
    else:
        print("\nFailed to apply import fix.")
        print("Please check the logs for details.")

if __name__ == "__main__":
    main() 