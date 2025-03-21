import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
import requests

from app.models import User, Job
from app.forms import LoginForm, RegistrationForm, SettingsForm, NewJobForm
from app.tasks import scrape_tweets_task, generate_audio_task, combine_audio_files_task
from config import Config

# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
jobs_bp = Blueprint('jobs', __name__)

# Main routes
@main_bp.route('/')
@main_bp.route('/index')
def index():
    """Home page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html', title='Welcome to TweedHat')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    # Get user's recent jobs
    jobs = Job.get_by_user_id(current_user.id)
    return render_template('dashboard.html', title='Dashboard', jobs=jobs, combined_audio_file=current_user.combined_audio_file)


@main_bp.route('/combine-audio', methods=['POST'])
@login_required
def combine_audio_files():
    """Combine all audio files from all jobs into a single file."""
    # Get all jobs for the user
    jobs = Job.get_by_user_id(current_user.id)
    
    # Check if there are any completed jobs with audio files
    has_audio_files = False
    for job in jobs:
        if job.status == 'completed' and job.audio_files:
            has_audio_files = True
            break
    
    if not has_audio_files:
        return jsonify({'success': False, 'error': 'No audio files found in your jobs.'}), 400
    
    try:
        # Start the task to combine audio files
        # We'll run this synchronously for immediate feedback
        output_file = combine_audio_files_task(current_user.id)
        
        if output_file:
            return jsonify({
                'success': True, 
                'file_path': output_file,
                'message': 'Audio files combined successfully!'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to combine audio files.'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/download-combined-audio')
@login_required
def download_combined_audio():
    """Download the combined audio file."""
    if not current_user.combined_audio_file or not os.path.exists(current_user.combined_audio_file):
        flash('Combined audio file not found.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    filename = os.path.basename(current_user.combined_audio_file)
    return send_file(current_user.combined_audio_file, as_attachment=True, download_name=f"tweedhat_combined_{filename}")


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page."""
    form = SettingsForm()
    
    if form.validate_on_submit():
        # Update user settings
        if form.elevenlabs_api_key.data:
            current_user.set_setting('elevenlabs_api_key', form.elevenlabs_api_key.data)
        if form.anthropic_api_key.data:
            current_user.set_setting('anthropic_api_key', form.anthropic_api_key.data)
        if form.twitter_email.data:
            current_user.set_setting('twitter_email', form.twitter_email.data)
        if form.twitter_password.data:
            current_user.set_setting('twitter_password', form.twitter_password.data)
        if form.default_voice_id.data:
            current_user.set_setting('default_voice_id', form.default_voice_id.data)
        
        flash('Your settings have been updated.', 'success')
        return redirect(url_for('main.settings'))
    
    # Pre-fill form with existing settings
    if not form.is_submitted():
        form.elevenlabs_api_key.data = current_user.get_setting('elevenlabs_api_key') or ''
        form.anthropic_api_key.data = current_user.get_setting('anthropic_api_key') or ''
        form.twitter_email.data = current_user.get_setting('twitter_email') or ''
        form.twitter_password.data = current_user.get_setting('twitter_password') or ''
        form.default_voice_id.data = current_user.settings.get('default_voice_id', '')
    
    return render_template('settings.html', title='Settings', form=form)


@main_bp.route('/voices')
@login_required
def list_voices():
    """List available voices from ElevenLabs."""
    api_key = current_user.get_setting('elevenlabs_api_key')
    
    if not api_key:
        flash('Please set your ElevenLabs API key in settings.', 'warning')
        return redirect(url_for('main.settings'))
    
    try:
        headers = {
            "xi-api-key": api_key
        }
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        response.raise_for_status()
        
        voices_data = response.json()
        voices = voices_data.get("voices", [])
        
        return render_template('voices.html', title='Available Voices', voices=voices)
    except Exception as e:
        flash(f'Error listing voices: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))


# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_username(form.username.data)
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        user.update_last_login()
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.dashboard')
        
        return redirect(next_page)
    
    return render_template('login.html', title='Sign In', form=form)


@auth_bp.route('/logout')
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        user.save()
        
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', title='Register', form=form)


# Jobs routes
@jobs_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_job():
    """Create a new job."""
    # Check if user has set required API keys
    elevenlabs_api_key = current_user.get_setting('elevenlabs_api_key')
    
    if not elevenlabs_api_key:
        flash('Please set your ElevenLabs API key in settings.', 'warning')
        return redirect(url_for('main.settings'))
    
    # Create form and populate voice choices
    form = NewJobForm()
    
    try:
        # Get available voices from ElevenLabs
        headers = {
            "xi-api-key": elevenlabs_api_key
        }
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        response.raise_for_status()
        
        voices_data = response.json()
        voices = voices_data.get("voices", [])
        
        # Populate voice choices
        form.voice_id.choices = [(voice['voice_id'], voice['name']) for voice in voices]
        
        # Set default voice if available
        default_voice_id = current_user.settings.get('default_voice_id')
        if default_voice_id and not form.is_submitted():
            form.voice_id.data = default_voice_id
    except Exception as e:
        flash(f'Error fetching voices: {str(e)}', 'danger')
        form.voice_id.choices = [('21m00Tcm4TlvDq8ikWAM', 'Rachel (Default)')]
    
    if form.validate_on_submit():
        # Create a new job
        job = Job(
            user_id=current_user.id,
            target_twitter_handle=form.target_twitter_handle.data,
            max_tweets=form.max_tweets.data or 20,
            describe_images=form.describe_images.data,
            voice_id=form.voice_id.data
        )
        job.save()
        
        # Start the job
        scrape_tweets_task.delay(job.id)
        
        flash('Job created successfully!', 'success')
        return redirect(url_for('jobs.view', job_id=job.id))
    
    return render_template('new_job.html', title='New Job', form=form)


@jobs_bp.route('/<job_id>')
@login_required
def view(job_id):
    """View job details."""
    job = Job.get_by_id(job_id)
    
    if not job or job.user_id != current_user.id:
        flash('Job not found.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('view_job.html', title='Job Details', job=job)


@jobs_bp.route('/<job_id>/status')
@login_required
def status(job_id):
    """Get job status (for AJAX requests)."""
    job = Job.get_by_id(job_id)
    
    if not job or job.user_id != current_user.id:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({
        'status': job.status,
        'updated_at': job.updated_at,
        'audio_files': job.audio_files,
        'error': job.error
    })


@jobs_bp.route('/<job_id>/download/<filename>')
@login_required
def download_audio(job_id, filename):
    """Download an audio file."""
    job = Job.get_by_id(job_id)
    
    if not job or job.user_id != current_user.id:
        flash('Job not found.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Find the full path of the audio file in the job's audio_files list
    file_path = None
    for audio_file in job.audio_files:
        if os.path.basename(audio_file) == filename:
            file_path = audio_file
            break
    
    if not file_path or not os.path.exists(file_path):
        flash('File not found.', 'danger')
        return redirect(url_for('jobs.view', job_id=job.id))
    
    return send_file(file_path, as_attachment=True)


@jobs_bp.route('/<job_id>/stream/<filename>')
@login_required
def stream_audio(job_id, filename):
    """Stream an audio file."""
    job = Job.get_by_id(job_id)
    
    if not job or job.user_id != current_user.id:
        return jsonify({'error': 'Job not found'}), 404
    
    # Find the full path of the audio file in the job's audio_files list
    file_path = None
    for audio_file in job.audio_files:
        if os.path.basename(audio_file) == filename:
            file_path = audio_file
            break
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=False)


@jobs_bp.route('/<job_id>/audio_files')
@login_required
def get_audio_files(job_id):
    """Get all audio files for a job in the correct order."""
    job = Job.get_by_id(job_id)
    
    if not job or job.user_id != current_user.id:
        return jsonify({'error': 'Job not found'}), 404
    
    # Extract filenames and sort them by tweet index
    audio_files = []
    for audio_file in job.audio_files:
        filename = os.path.basename(audio_file)
        # Extract the index from the filename (format: tweet_INDEX_ID.mp3)
        try:
            index = int(filename.split('_')[1])
            audio_files.append({
                'index': index,
                'filename': filename,
                'url': url_for('jobs.stream_audio', job_id=job.id, filename=filename)
            })
        except (IndexError, ValueError):
            # If we can't extract the index, just add it to the end
            audio_files.append({
                'index': 999,
                'filename': filename,
                'url': url_for('jobs.stream_audio', job_id=job.id, filename=filename)
            })
    
    # Sort by index
    audio_files.sort(key=lambda x: x['index'])
    
    return jsonify({'audio_files': audio_files})


@jobs_bp.route('/<job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    """Delete a job."""
    job = Job.get_by_id(job_id)
    
    if not job or job.user_id != current_user.id:
        flash('Job not found.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Delete associated files
    if job.tweet_file and os.path.exists(job.tweet_file):
        os.remove(job.tweet_file)
    
    for audio_file in job.audio_files:
        if os.path.exists(audio_file):
            os.remove(audio_file)
    
    # Delete job file
    os.remove(job.get_file_path())
    
    flash('Job deleted successfully.', 'success')
    return redirect(url_for('main.dashboard')) 