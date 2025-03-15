#!/bin/bash

# Print header
echo "====================================="
echo "  TweedHat Log Monitor  "
echo "====================================="

# Check if the log files exist
if [ ! -f "tweedhat-web/tweedhat-web.log" ]; then
    echo "Log file not found: tweedhat-web/tweedhat-web.log"
    echo "Make sure the application is running."
    exit 1
fi

# Function to monitor logs
monitor_logs() {
    echo "Monitoring logs for job activity..."
    echo "Press Ctrl+C to stop monitoring."
    echo ""
    
    # Use tail to follow the log file and grep for job-related entries
    tail -f tweedhat-web/tweedhat-web.log | grep --color=auto -E "Job|job|task|Task|progress|Progress|tweet|Tweet|audio|Audio|error|Error|failed|Failed"
}

# Function to show recent job activity
show_recent_activity() {
    echo "Recent job activity:"
    echo "===================="
    
    # Show recent job-related log entries
    grep -E "Job|job|task|Task|progress|Progress|tweet|Tweet|audio|Audio" tweedhat-web/tweedhat-web.log | tail -n 20
    
    echo ""
    echo "Recent errors (if any):"
    echo "======================="
    
    # Show recent error entries
    grep -E "error|Error|failed|Failed|exception|Exception" tweedhat-web/tweedhat-web.log | tail -n 10
    
    echo ""
}

# Function to check Celery worker status
check_celery_status() {
    echo "Checking Celery worker status..."
    echo "================================"
    
    # Check if Celery worker is running
    if pgrep -f "celery -A app.celery worker" > /dev/null; then
        echo "Celery worker is running."
        
        # Check Celery logs
        if [ -f "tweedhat-web/celery.log" ]; then
            echo ""
            echo "Recent Celery log entries:"
            tail -n 10 tweedhat-web/celery.log
        else
            echo "Celery log file not found."
        fi
    else
        echo "Celery worker is NOT running!"
        echo "Jobs will not be processed until the Celery worker is started."
        echo "Try restarting the application with ./start_tweedhat.sh"
    fi
    
    echo ""
}

# Show menu
echo "1. Monitor logs in real-time"
echo "2. Show recent job activity"
echo "3. Check Celery worker status"
echo "4. Exit"
echo ""
echo -n "Enter your choice (1-4): "
read choice

case $choice in
    1)
        monitor_logs
        ;;
    2)
        show_recent_activity
        ;;
    3)
        check_celery_status
        ;;
    4)
        echo "Exiting."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac
