#!/bin/bash

# Print header
echo "====================================="
echo "  Starting Celery Worker in Debug Mode  "
echo "====================================="

# Check if Redis is running
echo -n "Checking Redis... "
if redis-cli ping > /dev/null 2>&1; then
    echo "Running"
else
    echo "Not running, starting Redis..."
    redis-server --daemonize yes
    sleep 1
    if redis-cli ping > /dev/null 2>&1; then
        echo "Redis started successfully"
    else
        echo "Failed to start Redis. Please install and start Redis manually."
        exit 1
    fi
fi

# Create a celeryconfig.py file to ensure Redis is used
echo "Creating Celery configuration..."
cat > tweedhat-web/celeryconfig.py << EOF
# Celery configuration
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
enable_utc = True
worker_hijack_root_logger = False
broker_connection_retry_on_startup = True
task_track_started = True
worker_send_task_events = True
task_send_sent_event = True
EOF

# Kill any existing Celery workers
echo "Stopping any existing Celery workers..."
pkill -f "celery -A app.celery worker" || true
sleep 1

# Start Celery worker in the foreground with verbose logging
echo "Starting Celery worker in debug mode..."
cd tweedhat-web

# Set environment variables for Celery
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/0"
export CELERY_CONFIG_MODULE="celeryconfig"

# Start Celery worker with verbose logging
echo "Celery worker starting with verbose logging..."
echo "Press Ctrl+C to stop the worker"
celery -A app.celery worker --loglevel=debug 