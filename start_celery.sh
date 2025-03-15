#!/bin/bash

# Change to the tweedhat-web directory
cd tweedhat-web

# Set the broker URL to Redis
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/0"

# Start the Celery worker
celery -A app.celery worker --loglevel=info

# If the above command fails, try this alternative
# python -m celery -A app.celery worker --loglevel=info 