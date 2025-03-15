import os
import sys
import json
import requests
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the User model
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tweedhat-web'))
    from app.models import User
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

def check_elevenlabs_key(user_id):
    """Check if the ElevenLabs API key for a user is valid."""
    user = User.get_by_id(user_id)
    if not user:
        print(f"User not found: {user_id}")
        return False
    
    # Get the API key
    api_key = user.get_decrypted_setting('elevenlabs_api_key')
    if not api_key:
        print(f"No ElevenLabs API key found for user: {user.username}")
        return False
    
    # Check if the API key is valid
    try:
        headers = {
            "xi-api-key": api_key
        }
        print(f"Making request to ElevenLabs API with key: {api_key[:5]}...{api_key[-5:]}")
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        
        if response.status_code == 200:
            print(f"API key is valid for user: {user.username}")
            voices = response.json().get("voices", [])
            print(f"Found {len(voices)} voices")
            return True
        else:
            print(f"API key is invalid for user: {user.username}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error checking API key: {e}")
        return False

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
        # If there's only one user, check that user
        user_id, username = users[0]
        print(f"\nChecking ElevenLabs API key for user: {username}")
        check_elevenlabs_key(user_id)
    else:
        # Ask which user to check
        try:
            choice = int(input("\nEnter the number of the user to check: "))
            if 1 <= choice <= len(users):
                user_id, username = users[choice-1]
                print(f"\nChecking ElevenLabs API key for user: {username}")
                check_elevenlabs_key(user_id)
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")

if __name__ == "__main__":
    main() 