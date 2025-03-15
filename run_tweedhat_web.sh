#!/bin/bash

# TweedHat Web Application Launcher
# This script starts all components needed for the TweedHat web application:
# - Redis server (for Celery message broker)
# - Celery worker
# - Flask web application

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║                 TweedHat Web Application                   ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a process is running on a port
check_port() {
    if command_exists lsof; then
        lsof -i:"$1" >/dev/null 2>&1
        return $?
    elif command_exists netstat; then
        netstat -tuln | grep ":$1 " >/dev/null 2>&1
        return $?
    else
        echo -e "${YELLOW}Warning: Cannot check if port $1 is in use (lsof or netstat not available)${NC}"
        return 1
    fi
}

# Check for required commands
if ! command_exists redis-server; then
    echo -e "${RED}Error: redis-server is not installed. Please install Redis first.${NC}"
    echo "On macOS: brew install redis"
    echo "On Ubuntu/Debian: sudo apt install redis-server"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}Error: python3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

# Set up environment variables
export FLASK_APP=run.py
export FLASK_ENV=development

# Create tweedhat-web directory if it doesn't exist
if [ ! -d "tweedhat-web" ]; then
    echo -e "${RED}Error: tweedhat-web directory not found in the current location.${NC}"
    echo "Please run this script from the root directory of the TweedHat project."
    exit 1
fi

# Check if .env file exists in the tweedhat-web directory
if [ ! -f "tweedhat-web/.env" ]; then
    echo -e "${YELLOW}Warning: No .env file found in tweedhat-web directory.${NC}"
    echo "Creating a basic .env file with default values..."
    
    # Generate random key for Flask
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
    
    cat > tweedhat-web/.env << EOF
# TweedHat Web Application Environment Variables
SECRET_KEY=${SECRET_KEY}
FLASK_APP=run.py
FLASK_ENV=development

# Celery settings
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Data storage settings
DATA_DIRECTORY=data

# Storage settings - plaintext only
USE_PLAINTEXT=true
EOF
    echo -e "${GREEN}Created .env file with default values.${NC}"
    echo "Please edit this file to add your API keys if needed."
fi

# Load environment variables from .env file
if [ -f "tweedhat-web/.env" ]; then
    export $(grep -v '^#' tweedhat-web/.env | xargs)
fi

# Check if Redis is already running
if check_port 6379; then
    echo -e "${YELLOW}Redis is already running on port 6379.${NC}"
else
    echo -e "${GREEN}Starting Redis server...${NC}"
    redis-server --daemonize yes
    
    # Wait for Redis to start
    sleep 2
    
    if check_port 6379; then
        echo -e "${GREEN}Redis server started successfully.${NC}"
    else
        echo -e "${RED}Failed to start Redis server. Please start it manually.${NC}"
        exit 1
    fi
fi

# Change to the tweedhat-web directory
cd tweedhat-web || { echo -e "${RED}Error: tweedhat-web directory not found${NC}"; exit 1; }

# Create data directories if they don't exist
mkdir -p data
mkdir -p data/users
mkdir -p data/jobs
mkdir -p data/tweets
mkdir -p data/audio

echo -e "${GREEN}Created data directories for JSON storage.${NC}"

# Install required Python packages
echo -e "${GREEN}Checking for required Python packages...${NC}"

# Check if requirements files exist and install from them
if [ -f "requirements-web.txt" ]; then
    echo -e "${GREEN}Found requirements-web.txt. Installing packages...${NC}"
    pip install -r requirements-web.txt
elif [ -f "../requirements-web.txt" ]; then
    echo -e "${GREEN}Found requirements-web.txt in parent directory. Installing packages...${NC}"
    pip install -r ../requirements-web.txt
elif [ -f "requirements.txt" ]; then
    echo -e "${GREEN}Found requirements.txt. Installing packages...${NC}"
    pip install -r requirements.txt
elif [ -f "../requirements.txt" ]; then
    echo -e "${GREEN}Found requirements.txt in parent directory. Installing packages...${NC}"
    pip install -r ../requirements.txt
else
    echo -e "${RED}No requirements files found. Please create a requirements.txt or requirements-web.txt file.${NC}"
    echo -e "${RED}The application may not function correctly without required packages.${NC}"
    exit 1
fi

echo -e "${GREEN}All required packages installed successfully.${NC}"

# Kill any existing Celery workers
echo -e "${GREEN}Stopping any existing Celery workers...${NC}"
pkill -f "celery -A app.celery worker" || true
sleep 2

# Start Celery worker in the background
echo -e "${GREEN}Starting Celery worker...${NC}"
celery -A app.celery worker --loglevel=info > celery.log 2>&1 &
CELERY_PID=$!

# Check if Celery started successfully
sleep 3
if ps -p $CELERY_PID > /dev/null; then
    echo -e "${GREEN}Celery worker started with PID: $CELERY_PID${NC}"
else
    echo -e "${RED}Failed to start Celery worker. Check celery.log for details.${NC}"
    cat celery.log
    echo -e "\n${YELLOW}Attempting to fix common issues...${NC}"
    exit 1
fi

# Process any pending jobs
echo -e "${GREEN}Processing pending jobs...${NC}"
python3 process_pending_jobs.py

# Start Flask application
echo -e "${GREEN}Starting Flask application...${NC}"
echo -e "${BLUE}The web application will be available at: http://localhost:5001${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Trap Ctrl+C to ensure clean shutdown
trap 'echo -e "\n${GREEN}Shutting down services...${NC}"; \
      if ps -p $CELERY_PID > /dev/null; then \
          echo "Stopping Celery worker (PID: $CELERY_PID)..."; \
          kill $CELERY_PID; \
      fi; \
      echo "Stopping Redis server..."; \
      redis-cli shutdown; \
      echo -e "${GREEN}All services stopped. Goodbye!${NC}"; \
      exit 0' INT

# Check if port 5001 is already in use
if check_port 5001; then
    echo -e "${RED}Port 5001 is already in use. Please stop the existing service or use a different port.${NC}"
    echo -e "${YELLOW}Trying port 5002 instead...${NC}"
    python3 run.py --port=5002
else
    # Start Flask app
    python3 run.py
fi

# If Flask exits normally, also clean up
echo -e "\n${GREEN}Shutting down services...${NC}"

# Kill Celery worker
if ps -p $CELERY_PID > /dev/null; then
    echo "Stopping Celery worker (PID: $CELERY_PID)..."
    kill $CELERY_PID
fi

# Stop Redis server
echo "Stopping Redis server..."
redis-cli shutdown

echo -e "${GREEN}All services stopped. Goodbye!${NC}" 