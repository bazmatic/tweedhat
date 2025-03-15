import os
from flask import Flask
from flask_login import LoginManager
from celery import Celery
from datetime import datetime

from config import config

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Initialize Celery
celery = Celery(__name__, 
                broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
                backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
                include=['app.tasks'])

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions with app
    login_manager.init_app(app)
    
    # Configure Celery
    celery.conf.update(app.config)
    
    # Add context processor for template variables
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # Register blueprints
    from app.routes import main_bp, auth_bp, jobs_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(jobs_bp, url_prefix='/jobs')
    
    return app

# Import models to ensure they are registered with login_manager
from app import models 