FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_APP=run.py

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    xvfb \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    ca-certificates \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome or Chromium based on architecture and availability
RUN set -e \
    && if [ "$(uname -m)" = "x86_64" ]; then \
        # Try installing Chrome from the official repository
        apt-get update \
        && (wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - || true) \
        && (echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list || true) \
        && apt-get update \
        && (apt-get install -y google-chrome-stable || \
            # Fallback to Chromium if Chrome installation fails
            (apt-get install -y chromium || apt-get install -y chromium-browser) \
            && (ln -sf /usr/bin/chromium /usr/bin/google-chrome || ln -sf /usr/bin/chromium-browser /usr/bin/google-chrome)) \
        && rm -rf /var/lib/apt/lists/*; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        apt-get update \
        && (apt-get install -y chromium || apt-get install -y chromium-browser) \
        && (ln -sf /usr/bin/chromium /usr/bin/google-chrome || ln -sf /usr/bin/chromium-browser /usr/bin/google-chrome) \
        && rm -rf /var/lib/apt/lists/*; \
    fi \
    # Verify Chrome/Chromium is installed
    && (google-chrome --version || echo "WARNING: Chrome/Chromium installation may have failed, but continuing build")

# Create app directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements-web.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application code
COPY scrape.py .
COPY tweedhat.py .
COPY ai_integration.py .
COPY read_tweets.py .
COPY tweedhat-web/ ./tweedhat-web/

# Create necessary directories
RUN mkdir -p tweets images tweet_audio

# Set working directory to the web app
WORKDIR /app/tweedhat-web

# Create data directory for SQLite database
RUN mkdir -p data

# Expose port
EXPOSE 5001

# Run gunicorn with production settings
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "120", "run:app"] 