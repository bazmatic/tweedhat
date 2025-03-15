#!/bin/bash

# Print header
echo "====================================="
echo "  Starting TweedHat Web Application  "
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

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p tweedhat-web/data/users
mkdir -p tweedhat-web/data/tweets
mkdir -p tweedhat-web/data/images
mkdir -p tweedhat-web/data/audio
mkdir -p tweedhat-web/data/jobs

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

# Apply enhanced job logging
echo "Setting up enhanced job logging..."
if [ -f "enhance_job_logging.py" ]; then
    python enhance_job_logging.py --apply
else
    echo "Warning: enhance_job_logging.py not found. Enhanced logging will not be applied."
fi

# Start Celery worker in the background
echo "Starting Celery worker..."
cd tweedhat-web

# Set environment variables for Celery
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/0"
export CELERY_CONFIG_MODULE="celeryconfig"

# Kill any existing Celery workers
pkill -f "celery -A app.celery worker" || true
sleep 1

# Start Celery worker with Redis broker
celery -A app.celery worker --loglevel=info > celery.log 2>&1 &
CELERY_PID=$!
cd ..

# Check if Celery worker started successfully
sleep 3
if ps -p $CELERY_PID > /dev/null; then
    echo "Celery worker started successfully (PID: $CELERY_PID)"
    
    # Check if Celery is using Redis
    cd tweedhat-web
    echo "Checking Celery configuration..."
    grep "transport:" celery.log | tail -1
    cd ..
    
    # Verify tasks are registered
    echo "Checking registered tasks..."
    cd tweedhat-web
    python -c "from app import celery; print('Registered tasks:'); print('\n'.join(['- ' + task for task in sorted(celery.tasks.keys()) if not task.startswith('celery.')]))" || echo "Could not check registered tasks"
    cd ..
else
    echo "Failed to start Celery worker. Check celery.log for details."
    # Try alternative method
    echo "Trying alternative method to start Celery..."
    cd tweedhat-web
    python -m celery -A app.celery worker --loglevel=info > celery.log 2>&1 &
    CELERY_PID=$!
    cd ..
    sleep 3
    if ps -p $CELERY_PID > /dev/null; then
        echo "Celery worker started successfully with alternative method (PID: $CELERY_PID)"
    else
        echo "Failed to start Celery worker with alternative method. Please check celery.log for details."
        # Continue anyway, as the web app can still run without Celery
    fi
fi

# Make sure our monitoring scripts are executable
echo "Setting up monitoring tools..."
chmod +x check_job_status.py
chmod +x monitor_logs.sh

# Install required packages for monitoring tools
echo "Checking for required packages..."
pip install tabulate > /dev/null 2>&1

# Enhance the app/__init__.py file to properly configure Celery
echo "Checking app/__init__.py for Celery configuration..."
if [ -f "tweedhat-web/app/__init__.py" ]; then
    # Create a backup
    cp tweedhat-web/app/__init__.py tweedhat-web/app/__init__.py.bak
    
    # Add Celery configuration if needed
    if ! grep -q "CELERY_CONFIG_MODULE" tweedhat-web/app/__init__.py; then
        echo "Enhancing Celery configuration in app/__init__.py..."
        sed -i.tmp '/celery.conf.update(app.config)/a\\n    # Ensure Redis is used for Celery\n    if os.environ.get("CELERY_CONFIG_MODULE"):\n        celery.config_from_envvar("CELERY_CONFIG_MODULE")\n    celery.conf.update(broker_url="redis://localhost:6379/0", result_backend="redis://localhost:6379/0")' tweedhat-web/app/__init__.py
        rm -f tweedhat-web/app/__init__.py.tmp
    fi
fi

# Display monitoring instructions
echo ""
echo "====================================="
echo "  TweedHat Monitoring Tools  "
echo "====================================="
echo ""
echo "To monitor job status, open a new terminal and run:"
echo "  python check_job_status.py"
echo ""
echo "To monitor logs in real-time, open a new terminal and run:"
echo "  ./monitor_logs.sh"
echo ""
echo "To test job creation, open a new terminal and run:"
echo "  ./test_job.py"
echo ""
echo "====================================="

# Start the web application
echo "Starting web application..."
echo "The web application will be available at http://localhost:5003"
echo "Press Ctrl+C to stop all services"
echo ""

# Start the web application in the foreground
cd tweedhat-web
python run.py

# This part will only execute when the web application is stopped
echo "Web application stopped"

# Clean up - kill Celery worker
if ps -p $CELERY_PID > /dev/null; then
    echo "Stopping Celery worker (PID: $CELERY_PID)..."
    kill $CELERY_PID
fi

echo "TweedHat shutdown complete" 