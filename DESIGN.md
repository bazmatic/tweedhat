# TweedHat - Technical Design Document

## Project Overview

TweedHat is a tool that scrapes tweets from X.com (formerly Twitter) and reads them aloud using ElevenLabs' text-to-speech API. The project also includes AI-powered image description capabilities for tweets containing images, using either Anthropic's Claude or OpenAI's GPT-4 Vision models. TweedHat is available both as a command-line tool and as a web application.

## System Architecture

The project is structured into several key components:

### 1. Tweet Scraper (`scrape.py`)

The scraper component is responsible for collecting tweets from X.com profiles. It uses:

- **Selenium WebDriver**: For browser automation to navigate X.com
- **Chrome/Chromium**: As the browser engine
- **Nitter.net**: As an alternative source for scraping when direct X.com access is challenging

The scraper saves tweets in a standardized JSON format that includes:
- Tweet text
- Timestamp
- Media links (if available)
- Tweet statistics
- Source information

### 2. Tweet Reader (`read_tweets.py`)

The reader component processes the JSON files produced by the scraper and:

- Formats tweets for better listening experience
- Converts text to speech using ElevenLabs API
- Plays audio using either pygame or system audio players
- Optionally saves audio files
- Integrates with AI for image description

### 3. AI Integration (`ai_integration.py`)

The AI integration module provides image description capabilities:

- Supports both Anthropic Claude and OpenAI GPT-4 Vision models
- Downloads and processes images from URLs
- Handles image resizing for large images (>5MB)
- Provides detailed descriptions of images in tweets

### 4. Main Interface (`tweedhat.py`)

The main script ties all components together:

- Provides a unified command-line interface
- Handles argument parsing
- Coordinates the scraping and reading processes
- Manages error handling and logging

### 5. Web Application (`tweedhat-web/`)

The web application provides a user-friendly interface to TweedHat's functionality:

- **Flask Framework**: Powers the web application backend
- **Celery**: Handles asynchronous task processing for tweet scraping and audio generation
- **Redis**: Serves as the message broker for Celery tasks
- **JSON Files**: Stores user data, jobs, and application state in plaintext
- **Bootstrap**: Provides responsive UI components

Key web app components:
- User authentication and account management
- Simple API key storage (plaintext for POC)
- Job creation, monitoring, and history
- Audio file downloads
- Settings management

### 6. Folder Structure

The project uses a dedicated folder structure to organize content:

- **tweets/**: Stores JSON files containing scraped tweets
- **images/**: Stores downloaded images from tweets for AI processing
- **tweet_audio/**: Stores generated audio files of tweets
- **tweedhat-web/**: Contains the web application
  - **app/**: Core application code
    - **templates/**: HTML templates
    - **static/**: CSS, JavaScript, and other static assets
    - **utils/**: Utility functions
  - **data/**: User data and job information
    - **users/**: JSON files for user accounts
    - **jobs/**: JSON files for job tracking
    - **tweets/**: JSON files for scraped tweets
    - **audio/**: Audio files generated for web app users
  - **config.py**: Application configuration

## Data Flow

### Command-Line Flow
1. User provides a Twitter/X.com username via command line
2. Scraper collects tweets and saves them to a JSON file in the `tweets/` folder
3. Reader loads the JSON file and processes each tweet
4. For tweets with images, the AI integration module downloads images to the `images/` folder and generates descriptions
5. Text (including image descriptions) is sent to ElevenLabs for speech synthesis
6. Audio is played back to the user and optionally saved to the `tweet_audio/` folder

### Web Application Flow
1. User logs in to the web application
2. User creates a new job by providing a Twitter/X.com username and job settings
3. Job is queued in Celery and processed asynchronously
4. Scraper collects tweets and saves them to a user-specific JSON file
5. Reader processes tweets and generates audio files
6. User is notified when the job is complete
7. User can download audio files or view job details

## Technical Implementation Details

### Tweet Scraping

The scraper uses a multi-strategy approach:

1. **Direct X.com Access**: Attempts to scrape directly from X.com using Selenium
2. **Nitter Fallback**: If direct access fails, falls back to scraping from nitter.net
3. **Authentication Handling**: Supports login to access more content
4. **Rate Limiting**: Implements delays and randomization to avoid detection

### Text-to-Speech

The system uses ElevenLabs' API for high-quality voice synthesis:

- Supports multiple voices (selectable via voice ID)
- Handles text formatting for better speech output
- Manages audio playback with proper timing

### AI Image Description

The AI integration supports two leading models:

- **Anthropic Claude**: Default model for image description
- **OpenAI GPT-4 Vision**: Alternative model

Key features:
- Automatic image resizing for large images
- Error handling for failed downloads or API issues
- Detailed, contextual descriptions of image content

### Web Application

The web application extends TweedHat's functionality with:

- **User Management**: Registration, authentication, and profile management
- **API Key Management**: Storage of ElevenLabs and AI provider API keys
- **Job System**: Creation, monitoring, and management of tweet scraping and reading jobs
- **Background Processing**: Asynchronous job execution using Celery
- **File Management**: Organization and access to generated audio files
- **Security**: CSRF protection and password hashing
- **JSON Storage**: Simple, file-based data storage for users, jobs, and application state

### Error Handling and Logging

The system implements comprehensive logging:

- Debug mode for detailed diagnostics
- Error capture and reporting
- Fallback mechanisms for various failure scenarios
- Job status tracking in the web application

## Dependencies

### Command-Line Tool
- Python 3.8+
- Selenium and WebDriver
- Requests
- Pygame (for audio playback)
- Mutagen (for audio duration detection)
- Python-dotenv (for environment variable management)
- LangChain, LangChain-Anthropic, LangChain-OpenAI (for AI integration)
- Pillow (for image processing)

### Web Application
- Flask (web framework)
- Flask-Login (user authentication)
- Flask-WTF (form handling)
- Celery (task queue)
- Redis (message broker)
- All command-line tool dependencies

## Configuration

### Command-Line Tool
The system uses a `.env` file for configuration:

```
# API Keys
ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"
ANTHROPIC_API_KEY="your_anthropic_api_key_here"
OPENAI_API_KEY="your_openai_api_key_here"

# AI Model Settings
AI_PROVIDER="anthropic"  # Options: "anthropic" or "openai"
ANTHROPIC_MODEL="claude-3-opus-20240229"  # For Anthropic
# OPENAI_MODEL="gpt-4-vision-preview"  # For OpenAI
```

### Web Application
The web application uses environment variables and a `config.py` file:

```python
# Secret keys
SECRET_KEY="your_flask_secret_key"

# Data storage settings
DATA_DIRECTORY="data"
USE_PLAINTEXT=true

# Celery settings
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

## Usage Instructions

### Command-Line Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/bazmatic/tweedhat.git
   cd tweedhat
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```

4. Add your API keys to the `.env` file:
   - Get an ElevenLabs API key from [ElevenLabs](https://elevenlabs.io/)
   - For image description, add either:
     - Anthropic API key from [Anthropic](https://www.anthropic.com/)
     - OpenAI API key from [OpenAI](https://openai.com/)

### Web Application Installation

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

### Quick Start Script

For convenience, a single bash script is provided to start all required components:

```bash
./run_tweedhat_web.sh
```

This script automates the entire startup process by:
- Checking for required dependencies (Redis, Python)
- Creating a default `.env` file with a secure random key if one doesn't exist
- Setting up data directories for JSON storage
- Starting Redis server if not already running
- Verifying required Python packages are installed
- Starting the Celery worker for background processing
- Launching the Flask web application
- Gracefully shutting down all components when you exit with Ctrl+C

This is the recommended way to run the web application during development.

### Command-Line Basic Usage

The main script `tweedhat.py` provides a unified interface:

```bash
python tweedhat.py <username> [options]
```

For example, to scrape and read tweets from Elon Musk:
```bash
python tweedhat.py elonmusk
```

### Web Application Usage

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

### Command-Line Options

#### Scraper Options
- `--max-tweets <number>`: Maximum number of tweets to scrape (default: 20)
- `--visible`: Run browser in visible mode (not headless)
- `--email <email>`: X.com login email
- `--password <password>`: X.com login password
- `--no-profile`: Do not use a persistent Chrome profile

#### Reader Options
- `--voice-id <id>`: ID of the voice to use
- `--save-audio`: Save audio files
- `--output-dir <directory>`: Directory to save audio files
- `--delay <seconds>`: Delay between tweets in seconds (default: 2)
- `--read-max <number>`: Maximum number of tweets to read
- `--describe-images`: Use AI to describe images in tweets

#### General Options
- `--debug`: Enable debug logging
- `--list-voices`: List available voices and exit
- `--json-file <file>`: Use existing JSON file instead of scraping

### Advanced Usage Examples

1. Scrape tweets, save audio files, and describe images:
   ```bash
   python tweedhat.py elonmusk --save-audio --describe-images
   ```

2. Use a specific voice and limit the number of tweets:
   ```bash
   python tweedhat.py nasa --voice-id "EXAVITQu4vr4xnSDxMaL" --max-tweets 5
   ```

3. List available voices:
   ```bash
   python tweedhat.py --list-voices
   ```

4. Use an existing JSON file:
   ```bash
   python tweedhat.py elonmusk --json-file elonmusk_tweets.json
   ```

5. Test AI image description directly:
   ```bash
   python test_ai_integration.py --image-url "https://example.com/image.jpg"
   ```

## Limitations and Considerations

1. **X.com Access**: X.com has bot detection that may block scraping attempts. Using a logged-in session improves success rates.

2. **API Costs**: ElevenLabs and AI services have usage limits and costs based on your subscription.

3. **Media Content**: The scraper may not always capture all media links from tweets, especially when using nitter.net.

4. **Performance**: Processing large numbers of tweets, especially with image descriptions, can be time-consuming.

5. **Rate Limiting**: Excessive use may trigger rate limiting from X.com, ElevenLabs, or AI providers.

6. **Web Application Security**: Ensure proper security measures when deploying the web application publicly.

7. **JSON Storage**: The file-based storage system is simple but has limitations:
   - No built-in transaction support
   - Limited query capabilities
   - Not suitable for high-concurrency environments
   - Requires careful file locking to prevent corruption

8. **Plaintext Storage**: This proof-of-concept uses plaintext storage for simplicity:
   - API keys and user credentials are stored without encryption
   - Not suitable for production use without additional security measures
   - Should be enhanced with proper encryption before any public deployment

## Troubleshooting

1. **Scraping Issues**:
   - Try using the `--visible` flag to see what's happening
   - Provide login credentials with `--email` and `--password`
   - Check the logs for specific errors

2. **Audio Playback Problems**:
   - Ensure pygame is installed correctly
   - Try saving audio with `--save-audio` and play files manually

3. **AI Integration Issues**:
   - Verify API keys in the `.env` file
   - Check network connectivity to API services
   - Enable debug logging with `--debug`

4. **Web Application Issues**:
   - Check Redis is running for Celery tasks
   - Verify database permissions
   - Check log files in the tweedhat-web directory

## Future Enhancements

1. Support for additional social media platforms
2. Improved media content extraction
3. More voice customization options
4. Enhanced AI capabilities for content analysis
5. GUI interface for easier use
6. Web application improvements:
   - Real-time job progress updates
   - User role management
   - API for third-party integration
   - Enhanced audio playback in browser
   - Optional database integration for higher traffic deployments
   - Proper encryption of sensitive data

## Security Notes

- API keys should be kept secure in the `.env` file
- The `.env` file should never be committed to version control
- Use caution when storing login credentials
- For web application deployment, ensure proper security measures:
  - Use HTTPS with a valid SSL certificate
  - Set secure and unique values for SECRET_KEY
  - Configure proper firewall rules
  - Regularly update dependencies
  - Implement proper encryption for sensitive data before production use 