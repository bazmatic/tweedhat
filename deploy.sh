#!/bin/bash

# TweedHat Docker Deployment Script
# This script automates the deployment of TweedHat using Docker

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
echo "║              TweedHat Docker Deployment                    ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Check if the .env.production file exists
if [ ! -f "tweedhat-web/.env.production" ]; then
    echo -e "${YELLOW}Warning: tweedhat-web/.env.production file not found.${NC}"
    echo -e "Creating from template..."
    
    # Copy the example .env file if it exists
    if [ -f "tweedhat-web/.env" ]; then
        cp tweedhat-web/.env tweedhat-web/.env.production
        echo -e "${GREEN}Created .env.production from .env template.${NC}"
    else
        echo -e "${RED}Error: No template .env file found. Please create tweedhat-web/.env.production manually.${NC}"
        exit 1
    fi
fi

# Generate secure keys for production
echo -e "${BLUE}Generating secure keys for production...${NC}"
python generate_production_keys.py

# Create necessary directories if they don't exist
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p tweets images tweet_audio tweedhat-web/data

# Build and start the Docker containers
echo -e "${BLUE}Building and starting Docker containers...${NC}"
docker compose down
docker compose up -d --build

# Check if containers are running
echo -e "${BLUE}Checking if containers are running...${NC}"
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}Deployment successful! TweedHat is now running.${NC}"
    echo -e "You can access the application at: http://localhost:5001"
    echo -e "To view logs, run: docker compose logs -f"
else
    echo -e "${RED}Deployment failed. Please check the logs with: docker compose logs${NC}"
    exit 1
fi

echo -e "${YELLOW}Important: For production use, make sure to:${NC}"
echo -e "1. Set up a reverse proxy (like Nginx) for SSL/TLS"
echo -e "2. Configure proper firewall rules"
echo -e "3. Regularly back up your data directories"
echo -e "4. See DOCKER_DEPLOYMENT.md for more details" 