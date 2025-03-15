# TweedHat Web Application

A web application for scraping tweets from X.com (formerly Twitter) and converting them to audio using ElevenLabs voice synthesis.

## Features

- User registration and authentication
- Plaintext storage of API keys and settings
- Twitter account scraping
- Text-to-speech conversion using ElevenLabs
- AI-powered image description (using Anthropic Claude)
- Background job processing
- Audio file downloads
- Job history and management

## Requirements

- Python 3.8+
- Redis (for Celery task queue)
- Chrome/Chromium (for web scraping)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tweedhat.git
   cd tweedhat
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r tweedhat-web/requirements-web.txt
   ```

4. Set up environment variables:
   ```bash
   export FLASK_APP=run.py
   export FLASK_ENV=development
   export SECRET_KEY=your-secret-key
   ```

   On Windows:
   ```bash
   set FLASK_APP=run.py
   set FLASK_ENV=development
   set SECRET_KEY=your-secret-key
   ```

5. Start Redis (required for Celery):
   ```bash
   redis-server
   ```

6. Start Celery worker:
   ```bash
   cd tweedhat-web
   celery -A app.celery worker --loglevel=info
   ```

7. Run the application:
   ```bash
   cd tweedhat-web
   flask run
   ```

8. Access the application at http://localhost:5000

## Usage

1. Register for an account
2. Add your API keys in the Settings page:
   - ElevenLabs API key (required for text-to-speech)
   - Anthropic API key (optional, for image description)
   - Twitter credentials (optional, improves scraping success)

3. Create a new job:
   - Enter the Twitter handle to scrape
   - Set the maximum number of tweets
   - Choose whether to describe images
   - Select a voice for the audio

4. Monitor job progress on the job details page
5. Download audio files when the job is complete

## Deployment

For production deployment:

1. Set a secure value for `SECRET_KEY`
2. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
   ```

3. Set up a reverse proxy with Nginx or Apache
4. Configure Redis for production use
5. Use a process manager like Supervisor for Celery workers

## Security Notes

- API keys are stored in plaintext JSON files
- Passwords are securely hashed
- CSRF protection is enabled on all forms
- Rate limiting is applied to prevent abuse
- This application is intended for personal use only

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [ElevenLabs](https://elevenlabs.io/) for the text-to-speech API
- [Anthropic](https://www.anthropic.com/) for the Claude AI model
- [Flask](https://flask.palletsprojects.com/) web framework
- [Celery](https://docs.celeryq.dev/) distributed task queue
- [Bootstrap](https://getbootstrap.com/) for the UI components 