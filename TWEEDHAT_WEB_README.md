# TweedHat Web Application

A web application for scraping tweets from X.com (formerly Twitter) and converting them to audio using ElevenLabs voice synthesis.

## Prerequisites

- Python 3.8+
- Redis (for Celery task queue)
- Chrome/Chromium (for web scraping)
- ElevenLabs API key (for text-to-speech)
- Anthropic API key (optional, for image description)

## Quick Start

The easiest way to start the application is to use the provided startup script:

```bash
./start_tweedhat.sh
```

This script will:
1. Check if Redis is running and start it if needed
2. Create necessary data directories
3. Start the Celery worker for background tasks
4. Start the web application

The web application will be available at http://localhost:5003

## Manual Setup

If you prefer to start the components manually:

1. Start Redis:
   ```bash
   redis-server --daemonize yes
   ```

2. Start the Celery worker:
   ```bash
   cd tweedhat-web
   export CELERY_BROKER_URL="redis://localhost:6379/0"
   export CELERY_RESULT_BACKEND="redis://localhost:6379/0"
   celery -A app.celery worker --loglevel=info
   ```

3. Start the web application:
   ```bash
   cd tweedhat-web
   python run.py
   ```

## Setting Up API Keys

After registering and logging in to the web application, you'll need to set up your API keys:

1. Get an ElevenLabs API key from [ElevenLabs](https://elevenlabs.io/)
2. (Optional) Get an Anthropic API key from [Anthropic](https://www.anthropic.com/)

If you're having issues with the web interface, you can use the provided utility script to update your API keys:

```bash
python update_elevenlabs_key.py
```

## Monitoring Tools

TweedHat includes several tools to help you monitor job progress and troubleshoot issues:

### Job Status Checker

The `check_job_status.py` script provides detailed information about all jobs in the system:

```bash
python check_job_status.py
```

Options:
- `--job-id <id>`: Show detailed information for a specific job
- `--all`: Show all jobs (not just the most recent ones)
- `--limit <number>`: Limit the number of jobs shown (default: 10)

### Log Monitor

The `monitor_logs.sh` script allows you to monitor the application logs in real-time:

```bash
./monitor_logs.sh
```

This tool provides:
- Real-time log monitoring with highlighting for important events
- Recent job activity summary
- Error detection and reporting

### Enhanced Job Logging

The `enhance_job_logging.py` script improves the logging of Celery tasks:

```bash
python enhance_job_logging.py --apply
```

This enhances the logging system to provide more detailed information about job progress and task execution.

## Troubleshooting

### Checking API Keys

You can check if your ElevenLabs API key is valid using the provided utility script:

```bash
python check_elevenlabs_key.py
```

### Celery Worker Issues

If the Celery worker fails to start, check the `tweedhat-web/celery.log` file for error messages.

Common issues:
- Redis not running
- Incorrect broker URL
- Python path issues

### Web Application Issues

If the web application fails to start, check the console output for error messages.

Common issues:
- Port 5003 already in use
- Missing dependencies
- Invalid API keys

### Job Not Starting

If your job is not starting:

1. Check the job status using `python check_job_status.py`
2. Monitor the logs using `./monitor_logs.sh`
3. Verify that the Celery worker is running (check `tweedhat-web/celery.log`)
4. Make sure your API keys are valid

## Directory Structure

- `tweedhat-web/`: Main web application directory
  - `app/`: Application code
  - `data/`: Data storage
    - `users/`: User data
    - `tweets/`: Scraped tweets
    - `audio/`: Generated audio files
    - `jobs/`: Job data
  - `run.py`: Web application entry point

## License

This project is licensed under the MIT License - see the LICENSE file for details. 