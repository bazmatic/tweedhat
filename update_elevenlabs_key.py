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

def update_elevenlabs_key(user_id, api_key):
    """Update the ElevenLabs API key for a user."""
    user = User.get_by_id(user_id)
    if not user:
        print(f"User not found: {user_id}")
        return False
    
    # Update the API key
    user.set_setting('elevenlabs_api_key', api_key)
    print(f"Updated ElevenLabs API key for user: {user.username}")
    
    # Verify the API key
    try:
        headers = {
            "xi-api-key": api_key
        }
        print(f"Verifying API key with ElevenLabs...")
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        
        if response.status_code == 200:
            print(f"API key is valid!")
            voices = response.json().get("voices", [])
            print(f"Found {len(voices)} voices")
            return True
        else:
            print(f"API key verification failed!")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error verifying API key: {e}")
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
    
    # Ask for the new API key
    api_key = input("\nEnter your ElevenLabs API key: ").strip()
    
    if not api_key:
        print("No API key provided. Nothing to update.")
        return
    
    # Update the API key
    update_elevenlabs_key(user_id, api_key)

if __name__ == "__main__":
    main() 