#!/usr/bin/env python3

import os
import sys
from pprint import pprint

# Add the current directory to the path
sys.path.insert(0, os.path.abspath('.'))

# Set environment variables
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
os.environ['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Import the app and celery
from tweedhat_web.app import create_app, celery

# Create the app
app = create_app('default')

# Print Celery configuration
print("Celery Configuration:")
print("====================")
pprint(celery.conf.humanize())

# Print registered tasks
print("\nRegistered Tasks:")
print("=================")
for task_name in sorted(celery.tasks.keys()):
    print(f"- {task_name}")

# Try to get task
print("\nTask Details:")
print("=============")
try:
    task = celery.tasks.get('app.tasks.scrape_tweets_task')
    print(f"Task: {task}")
    print(f"Name: {task.name}")
    print(f"Request: {task.request}")
except Exception as e:
    print(f"Error getting task: {e}")

# Try to send a test task
print("\nSending Test Task:")
print("=================")
try:
    from app.tasks import scrape_tweets_task
    result = scrape_tweets_task.delay('test_job_id')
    print(f"Task sent: {result}")
    print(f"Task ID: {result.id}")
    print(f"Task status: {result.status}")
except Exception as e:
    print(f"Error sending task: {e}") 