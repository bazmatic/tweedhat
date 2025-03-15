import os
import sys
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Get the ElevenLabs API key from environment variables
elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

if not elevenlabs_api_key:
    print("Error: ELEVENLABS_API_KEY not found in .env file")
    sys.exit(1)

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the User model and Config
try:
    from tweedhat_web.app.models import User
    from tweedhat_web.config import Config
except ImportError:
    try:
        # Try alternative import path
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tweedhat-web'))
        from app.models import User
        from config import Config
    except ImportError as e:
        print(f"Error: Could not import User model. {e}")
        sys.exit(1)

def list_users():
    """List all users in the system."""
    users_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tweedhat-web/data/users')
    if not os.path.exists(users_dir):
        print(f"Users directory not found: {users_dir}")
        return []
    
    users = []
    for filename in os.listdir(users_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(users_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                users.append((data['user_id'], data['username']))
    
    return users

def update_user_settings(user_id, elevenlabs_api_key=None, anthropic_api_key=None):
    """Update the settings for a specific user."""
    user = User.get_by_id(user_id)
    if not user:
        print(f"User not found: {user_id}")
        return False
    
    # Update settings
    if elevenlabs_api_key:
        user.set_setting('elevenlabs_api_key', elevenlabs_api_key)
        print(f"Updated ElevenLabs API key for user: {user.username}")
    
    if anthropic_api_key:
        user.set_setting('anthropic_api_key', anthropic_api_key)
        print(f"Updated Anthropic API key for user: {user.username}")
    
    return True

def main():
    """Main function."""
    print("Listing users...")
    users = list_users()
    
    if not users:
        print("No users found.")
        return
    
    print("\nAvailable users:")
    for i, (user_id, username) in enumerate(users):
        print(f"{i+1}. {username} ({user_id})")
    
    if len(users) == 1:
        # If there's only one user, update that user
        user_id, username = users[0]
        print(f"\nSelected user: {username}")
    else:
        # Ask which user to update
        try:
            choice = int(input("\nEnter the number of the user to update: "))
            if 1 <= choice <= len(users):
                user_id, username = users[choice-1]
                print(f"\nSelected user: {username}")
            else:
                print("Invalid choice.")
                return
        except ValueError:
            print("Invalid input. Please enter a number.")
            return
    
    # Ask for API keys
    elevenlabs_api_key = input("\nEnter your ElevenLabs API key (leave empty to skip): ").strip()
    anthropic_api_key = input("Enter your Anthropic API key (leave empty to skip): ").strip()
    
    if not elevenlabs_api_key and not anthropic_api_key:
        print("No API keys provided. Nothing to update.")
        return
    
    # Update user settings
    update_user_settings(user_id, elevenlabs_api_key, anthropic_api_key)
    print("\nSettings updated successfully!")

if __name__ == "__main__":
    main() 