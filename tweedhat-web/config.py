import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Application paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    # User data
    USERS_DIR = os.path.join(DATA_DIR, 'users')
    
    # Content directories
    TWEETS_DIR = os.path.join(DATA_DIR, 'tweets')
    IMAGES_DIR = os.path.join(DATA_DIR, 'images')
    AUDIO_DIR = os.path.join(DATA_DIR, 'audio')
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # Rate limiting
    RATELIMIT_DEFAULT = "5 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Ensure directories exist
    @staticmethod
    def init_app(app):
        os.makedirs(Config.USERS_DIR, exist_ok=True)
        os.makedirs(Config.TWEETS_DIR, exist_ok=True)
        os.makedirs(Config.IMAGES_DIR, exist_ok=True)
        os.makedirs(Config.AUDIO_DIR, exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True
    

class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production
    
    # Use Redis for rate limiting in production
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 