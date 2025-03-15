#!/usr/bin/env python
import os
import sys
from app import create_app, celery

app = create_app()
app.app_context().push()

if __name__ == '__main__':
    print("Starting Celery worker...")
    celery.worker_main(sys.argv) 