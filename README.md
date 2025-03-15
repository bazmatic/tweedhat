# TweedHat

A tool for scraping tweets from X.com (formerly Twitter) and reading them aloud using ElevenLabs voice synthesis.

## Features

- Scrape tweets from any public X.com profile
- Convert tweet text to speech using ElevenLabs API
- Save audio files of tweets
- Format tweets for better listening experience
- Handle URLs, hashtags, and mentions appropriately
- Detect and announce videos in tweets
- AI-powered image description for tweets containing images (using Anthropic or OpenAI)
- Web application interface with user accounts and job management

## Components

### Command-Line Interface

#### All-in-One Script (`tweedhat.py`)

Combines tweet scraping and reading in a single command.

```bash
python tweedhat.py USERNAME [options]
```

Options are grouped into scraper options and reader options:

Scraper options:
- `--max-tweets NUMBER`: Maximum number of tweets to scrape
- `--visible`: Run scraper in visible mode (not headless)
- `--email EMAIL`: X.com login email
- `--password PASSWORD`: X.com login password
- `--no-profile`: Do not use a persistent Chrome profile

Reader options:
- `--voice-id ID`: ID of the voice to use
- `--save-audio`: Save audio files
- `--output-dir DIR`: Directory to save audio files
- `--delay SECONDS`: Delay between tweets in seconds
- `--read-max NUMBER`: Maximum number of tweets to read

General options:
- `--debug`: Enable debug logging
- `--list-voices`: List available voices and exit
- `--json-file FILE`: Use existing JSON file instead of scraping

#### Tweet Scraper (`scrape.py`)

Scrapes tweets from X.com profiles using Selenium WebDriver.

```bash
python scrape.py USERNAME [options]
```

Options:
- `--max NUMBER`: Maximum number of tweets to scrape
- `--output FILENAME`: Custom output filename
- `--visible`: Run in visible mode (not headless)
- `--debug`: Enable debug logging
- `--email EMAIL`: X.com login email
- `--password PASSWORD`: X.com login password
- `--no-profile`: Do not use a persistent Chrome profile

#### Tweet Reader (`read_tweets.py`)

Reads tweets aloud using ElevenLabs voice synthesis.

```bash
python read_tweets.py JSON_FILE [options]
```

Options:
- `--api-key KEY`: ElevenLabs API key
- `--voice-id ID`: ID of the voice to use
- `--save-audio`: Save audio files
- `--output-dir DIR`: Directory to save audio files
- `--delay SECONDS`: Delay between tweets in seconds
- `--list-voices`: List available voices
- `--debug`: Enable debug logging
- `--max-tweets NUMBER`: Maximum number of tweets to read

### Web Application (`tweedhat-web/`)

A web-based interface for TweedHat that provides:

- User registration and authentication
- Storage of API keys (plaintext for this POC)
- Job creation and management
- Background processing of tweet scraping and audio generation
- Audio file downloads
- Job history and status tracking
- Simple JSON file-based data storage

#### Quick Start Script

For convenience, a single script is provided to start all required components (Redis, Celery, and Flask):

```bash
./run_tweedhat_web.sh
```

This script will:
- Check for required dependencies
- Start Redis server if not already running
- Create a default .env file if one doesn't exist
- Set up data directories for JSON storage
- Start the Celery worker for background processing
- Launch the Flask web application
- Gracefully shut down all components when you exit

To run the web application manually:

```bash
cd tweedhat-web
flask run
```

For production deployment, use a WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

## Setup

### Command-Line Tool

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on the `.env.example` template:
   ```
   cp .env.example .env
   ```
4. Add your API keys to the `.env` file:
   - Get an ElevenLabs API key from [ElevenLabs](https://elevenlabs.io/)
   - For image description, add either:
     - Anthropic API key from [Anthropic](https://www.anthropic.com/)
     - OpenAI API key from [OpenAI](https://openai.com/)

### Web Application

1. Install additional dependencies:
   ```bash
   pip install flask celery redis flask-login flask-wtf
   ```

2. Set up environment variables:
   ```bash
   export FLASK_APP=run.py
   export FLASK_ENV=development
   export SECRET_KEY=your-secret-key
   ```

3. Start Redis (required for Celery):
   ```bash
   redis-server
   ```

4. Start Celery worker:
   ```bash
   cd tweedhat-web
   celery -A app.celery worker --loglevel=info
   ```

5. Run the application:
   ```bash
   cd tweedhat-web
   flask run
   ```

6. Access the application at http://localhost:5000

Alternatively, use the all-in-one script:
```bash
./run_tweedhat_web.sh
```

## Usage

### Command-Line Interface

The main script `tweedhat.py` provides a command-line interface for scraping tweets and reading them aloud:

```
python tweedhat.py <username> [options]
```

#### Options

##### Scraper options:
- `--max-tweets <number>`: Maximum number of tweets to scrape (default: 20)
- `--headless`: Run browser in headless mode
- `--no-read`: Only scrape tweets, don't read them aloud

##### Reader options:
- `--voice-id <id>`: ID of the voice to use
- `--save-audio`: Save audio files
- `--output-dir <directory>`: Directory to save audio files
- `--delay <seconds>`: Delay between tweets in seconds (default: 2)
- `--read-max <number>`: Maximum number of tweets to read
- `--describe-images`: Use AI to describe images in tweets

##### General options:
- `--list-voices`: List available voices
- `--debug`: Enable debug logging

#### Examples

Scrape tweets from Elon Musk and read them aloud:
```
python tweedhat.py elonmusk
```

Scrape tweets, save audio files, and use AI to describe images:
```
python tweedhat.py elonmusk --save-audio --describe-images
```

List available voices:
```
python tweedhat.py --list-voices
```

### Web Application

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

## Notes

- The scraper works best when logged in to X.com
- X.com has bot detection that may block scraping attempts
- ElevenLabs has usage limits based on your subscription
- Keep your API key secure in the `.env` file and not committing it to version control
- The web application uses simple JSON file storage which is suitable for personal use but may not scale for high-traffic deployments
- This is a proof-of-concept that stores API keys and user data in plaintext - not suitable for production without additional security measures
- For web application deployment, ensure proper security measures:
  - Use HTTPS with a valid SSL certificate
  - Set secure values for SECRET_KEY
  - Configure proper firewall rules
  - Implement proper encryption for sensitive data before production use

## Troubleshooting

### Command-Line Tool
- If scraping fails, try using the `--visible` flag to see what's happening
- Provide login credentials with `--email` and `--password` for better results
- Enable debug logging with `--debug` for more detailed error information

### Web Application
- Ensure Redis is running for Celery task processing
- Check log files in the tweedhat-web directory for errors
- Verify database permissions and connectivity
- For Celery worker issues, run with `--loglevel=debug` for more information 