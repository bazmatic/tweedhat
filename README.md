# TweedHat

A tool for scraping tweets from X.com (formerly Twitter) and reading them aloud using ElevenLabs voice synthesis.

## Features

- Scrape tweets from any public X.com profile
- Convert tweet text to speech using ElevenLabs API
- Save audio files of tweets
- Format tweets for better listening experience
- Handle URLs, hashtags, and mentions appropriately
- Detect and announce videos in tweets

## Components

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
3. Get an ElevenLabs API key from [ElevenLabs](https://elevenlabs.io/)
4. Create a `.env` file in the project root with your API key:
   ```
   ELEVENLABS_API_KEY="your_api_key_here"
   ```
5. Run the scraper to collect tweets
6. Run the reader to listen to the tweets

## Example Usage

1. Scrape tweets from a user:
   ```bash
   python scrape.py elonmusk --visible --max 20
   ```

2. List available voices:
   ```bash
   python read_tweets.py example_tweet.json --list-voices
   ```

3. Read tweets with a specific voice:
   ```bash
   python read_tweets.py elonmusk_tweets_20250315_192935.json --voice-id "EXAVITQu4vr4xnSDxMaL" --max-tweets 5
   ```

4. Save audio files of tweets:
   ```bash
   python read_tweets.py elonmusk_tweets_20250315_192935.json --voice-id "EXAVITQu4vr4xnSDxMaL" --save-audio
   ```

## Notes

- The scraper works best when logged in to X.com
- X.com has bot detection that may block scraping attempts
- ElevenLabs has usage limits based on your subscription
- Keep your API key secure by using the `.env` file and not committing it to version control 