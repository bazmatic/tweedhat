import os
import json
import uuid
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from cryptography.fernet import Fernet
from app import login_manager
from config import Config

# Encryption key for sensitive data
# In production, this should be stored securely and not in the code
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

class User(UserMixin):
    """User model for authentication and storing user data in JSON files."""
    
    def __init__(self, id=None, username=None, password_hash=None, created_at=None, 
                 last_login=None, settings=None):
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at or datetime.now().isoformat()
        self.last_login = last_login or datetime.now().isoformat()
        self.settings = settings or {}
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_file_path(self):
        """Get the path to the user's JSON file."""
        return os.path.join(Config.USERS_DIR, f"{self.id}.json")
    
    def save(self):
        """Save user data to JSON file."""
        user_data = {
            'user_id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'settings': self.settings
        }
        
        # Encrypt sensitive settings
        encrypted_settings = {}
        for key, value in self.settings.items():
            if key in ['elevenlabs_api_key', 'anthropic_api_key', 'twitter_email', 'twitter_password']:
                if value:  # Only encrypt if value exists
                    encrypted_settings[key] = cipher_suite.encrypt(value.encode()).decode()
            else:
                encrypted_settings[key] = value
        
        user_data['settings'] = encrypted_settings
        
        with open(self.get_file_path(), 'w') as f:
            json.dump(user_data, f, indent=2)
    
    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.now().isoformat()
        self.save()
    
    def get_decrypted_setting(self, key):
        """Get a decrypted setting value."""
        if key not in self.settings:
            return None
        
        value = self.settings.get(key)
        if not value:
            return None
            
        if key in ['elevenlabs_api_key', 'anthropic_api_key', 'twitter_email', 'twitter_password']:
            try:
                return cipher_suite.decrypt(value.encode()).decode()
            except Exception:
                # If the value is not encrypted, return as is
                return value
        return value
    
    def set_setting(self, key, value):
        """Set a setting value."""
        self.settings[key] = value
        self.save()
    
    @staticmethod
    def get_by_id(user_id):
        """Get a user by ID."""
        file_path = os.path.join(Config.USERS_DIR, f"{user_id}.json")
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return User(
            id=data['user_id'],
            username=data['username'],
            password_hash=data['password_hash'],
            created_at=data['created_at'],
            last_login=data['last_login'],
            settings=data['settings']
        )
    
    @staticmethod
    def get_by_username(username):
        """Get a user by username."""
        # Since we don't have an index, we need to scan all files
        if not os.path.exists(Config.USERS_DIR):
            return None
            
        for filename in os.listdir(Config.USERS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(Config.USERS_DIR, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if data['username'] == username:
                    return User(
                        id=data['user_id'],
                        username=data['username'],
                        password_hash=data['password_hash'],
                        created_at=data['created_at'],
                        last_login=data['last_login'],
                        settings=data['settings']
                    )
        
        return None


class Job:
    """Job model for tracking tweet scraping and audio generation jobs."""
    
    def __init__(self, id=None, user_id=None, status="pending", created_at=None, 
                 updated_at=None, target_twitter_handle=None, max_tweets=20, 
                 describe_images=False, voice_id=None, tweet_file=None, 
                 audio_files=None, error=None, progress=None, progress_details=None):
        self.id = id or str(uuid.uuid4())
        self.user_id = user_id
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.target_twitter_handle = target_twitter_handle
        self.max_tweets = max_tweets
        self.describe_images = describe_images
        self.voice_id = voice_id
        self.tweet_file = tweet_file
        self.audio_files = audio_files or []
        self.error = error
        self.progress = progress or 0  # Percentage of completion (0-100)
        self.progress_details = progress_details or {}  # Detailed progress information
    
    def get_file_path(self):
        """Get the path to the job's JSON file."""
        return os.path.join(Config.DATA_DIR, 'jobs', f"{self.id}.json")
    
    def save(self):
        """Save job data to JSON file."""
        job_data = {
            'job_id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': datetime.now().isoformat(),
            'target_twitter_handle': self.target_twitter_handle,
            'max_tweets': self.max_tweets,
            'describe_images': self.describe_images,
            'voice_id': self.voice_id,
            'tweet_file': self.tweet_file,
            'audio_files': self.audio_files,
            'error': self.error,
            'progress': self.progress,
            'progress_details': self.progress_details
        }
        
        # Ensure jobs directory exists
        jobs_dir = os.path.join(Config.DATA_DIR, 'jobs')
        os.makedirs(jobs_dir, exist_ok=True)
        
        with open(self.get_file_path(), 'w') as f:
            json.dump(job_data, f, indent=2)
    
    def update_status(self, status, error=None, progress=None, progress_details=None):
        """
        Update job status and progress.
        
        Args:
            status (str): New status
            error (str, optional): Error message
            progress (int, optional): Progress percentage (0-100)
            progress_details (dict, optional): Detailed progress information
        """
        self.status = status
        self.updated_at = datetime.now().isoformat()
        
        if error:
            self.error = error
            
        if progress is not None:
            self.progress = progress
            
        if progress_details:
            if not self.progress_details:
                self.progress_details = {}
            self.progress_details.update(progress_details)
            
        # Set default progress based on status
        if progress is None:
            if status == "pending":
                self.progress = 0
            elif status == "scraping":
                self.progress = 10
            elif status == "scraped":
                self.progress = 20
            elif status == "generating_audio":
                self.progress = 30
            elif status == "completed":
                self.progress = 100
                
        # Add timestamp to progress details
        if not self.progress_details:
            self.progress_details = {}
        self.progress_details[f"status_{status}"] = datetime.now().isoformat()
        
        self.save()
    
    def add_audio_file(self, audio_file):
        """Add an audio file to the job."""
        if audio_file not in self.audio_files:
            self.audio_files.append(audio_file)
            self.save()
    
    def update_progress(self, current, total, stage="processing"):
        """
        Update job progress based on current/total items.
        
        Args:
            current (int): Current item number
            total (int): Total number of items
            stage (str): Current processing stage
        """
        if stage == "scraping":
            # Scraping is 0-20% of the process
            base = 0
            max_progress = 20
        elif stage == "processing":
            # Processing is 30-100% of the process
            base = 30
            max_progress = 100
        else:
            base = 0
            max_progress = 100
            
        if total > 0:
            stage_progress = (current / total) * (max_progress - base)
            self.progress = int(base + stage_progress)
        else:
            self.progress = base
            
        progress_details = {
            f"{stage}_current": current,
            f"{stage}_total": total,
            f"{stage}_percentage": round((current / total) * 100 if total > 0 else 0, 2)
        }
        
        self.update_status(
            status=self.status,
            progress=self.progress,
            progress_details=progress_details
        )
    
    @staticmethod
    def get_by_id(job_id):
        """Get a job by ID."""
        file_path = os.path.join(Config.DATA_DIR, 'jobs', f"{job_id}.json")
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return Job(
            id=data['job_id'],
            user_id=data['user_id'],
            status=data['status'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            target_twitter_handle=data['target_twitter_handle'],
            max_tweets=data['max_tweets'],
            describe_images=data['describe_images'],
            voice_id=data['voice_id'],
            tweet_file=data['tweet_file'],
            audio_files=data['audio_files'],
            error=data['error'],
            progress=data.get('progress', 0),
            progress_details=data.get('progress_details', {})
        )
    
    @staticmethod
    def get_by_user_id(user_id):
        """Get all jobs for a user."""
        jobs = []
        jobs_dir = os.path.join(Config.DATA_DIR, 'jobs')
        
        if not os.path.exists(jobs_dir):
            return jobs
            
        for filename in os.listdir(jobs_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(jobs_dir, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if data['user_id'] == user_id:
                    jobs.append(Job(
                        id=data['job_id'],
                        user_id=data['user_id'],
                        status=data['status'],
                        created_at=data['created_at'],
                        updated_at=data['updated_at'],
                        target_twitter_handle=data['target_twitter_handle'],
                        max_tweets=data['max_tweets'],
                        describe_images=data['describe_images'],
                        voice_id=data['voice_id'],
                        tweet_file=data['tweet_file'],
                        audio_files=data['audio_files'],
                        error=data['error'],
                        progress=data.get('progress', 0),
                        progress_details=data.get('progress_details', {})
                    ))
        
        # Sort by created_at (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return jobs


@login_manager.user_loader
def load_user(user_id):
    """Load a user for Flask-Login."""
    return User.get_by_id(user_id) 