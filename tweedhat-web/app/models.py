import os
import json
import uuid
import time
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login_manager
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

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
        
        # Store settings as plaintext
        with open(self.get_file_path(), 'w') as f:
            json.dump(user_data, f, indent=2)
    
    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.now().isoformat()
        self.save()
    
    def get_setting(self, key):
        """Get a setting value."""
        if key not in self.settings:
            return None
        
        return self.settings.get(key)
    
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
                 audio_files=None, error=None):
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
            'error': self.error
        }
        
        # Ensure jobs directory exists
        jobs_dir = os.path.join(Config.DATA_DIR, 'jobs')
        os.makedirs(jobs_dir, exist_ok=True)
        
        with open(self.get_file_path(), 'w') as f:
            json.dump(job_data, f, indent=2)
    
    def update_status(self, status, error=None):
        """Update job status."""
        old_status = self.status
        self.status = status
        self.updated_at = datetime.now().isoformat()
        if error:
            self.error = error
            logger.error(f"Job {self.id} (@{self.target_twitter_handle}) status changed: {old_status} -> {status}, Error: {error}")
        else:
            logger.info(f"Job {self.id} (@{self.target_twitter_handle}) status changed: {old_status} -> {status}")
        self.save()
    
    def add_audio_file(self, audio_file):
        """Add an audio file to the job."""
        if audio_file not in self.audio_files:
            self.audio_files.append(audio_file)
            self.save()
    
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
            error=data['error']
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
                        error=data['error']
                    ))
        
        return jobs

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.get_by_id(user_id) 