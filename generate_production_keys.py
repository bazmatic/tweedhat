#!/usr/bin/env python3
"""
Generate secure random keys for production environment.
Run this script before deploying to production to generate secure keys.
"""

import os
import secrets
import re

def generate_key():
    """Generate a secure random key."""
    return secrets.token_hex(16)

def update_env_file(file_path):
    """Update the .env.production file with secure random keys."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} does not exist.")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the placeholder keys with secure random keys
    content = re.sub(
        r'SECRET_KEY=CHANGE_THIS_TO_A_RANDOM_STRING_IN_PRODUCTION',
        f'SECRET_KEY={generate_key()}',
        content
    )
    
    content = re.sub(
        r'ENCRYPTION_KEY=CHANGE_THIS_TO_A_RANDOM_STRING_IN_PRODUCTION',
        f'ENCRYPTION_KEY={generate_key()}',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return True

if __name__ == "__main__":
    env_file = "tweedhat-web/.env.production"
    
    if update_env_file(env_file):
        print(f"Successfully updated {env_file} with secure random keys.")
        print("Make sure to keep these keys secret and never commit them to version control.")
    else:
        print(f"Failed to update {env_file}.") 