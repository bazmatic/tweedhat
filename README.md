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

## Components

### All-in-One Script (`tweedhat.py`)

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

### Tweet Scraper (`scrape.py`)

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

### Tweet Reader (`read_tweets.py`)

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

## Setup

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

## Usage

The main script `tweedhat.py` provides a command-line interface for scraping tweets and reading them aloud:

```
python tweedhat.py <username> [options]
```

### Options

#### Scraper options:
- `--max-tweets <number>`: Maximum number of tweets to scrape (default: 20)
- `--headless`: Run browser in headless mode
- `--no-read`: Only scrape tweets, don't read them aloud

#### Reader options:
- `--voice-id <id>`: ID of the voice to use
- `--save-audio`: Save audio files
- `--output-dir <directory>`: Directory to save audio files
- `--delay <seconds>`: Delay between tweets in seconds (default: 2)
- `--read-max <number>`: Maximum number of tweets to read
- `--describe-images`: Use AI to describe images in tweets

#### General options:
- `--list-voices`: List available voices
- `--debug`: Enable debug logging

### Examples

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

## Notes

- The scraper works best when logged in to X.com
- X.com has bot detection that may block scraping attempts
- ElevenLabs has usage limits based on your subscription
- Keep your API key secure by using the `.env` file and not committing it to version control 