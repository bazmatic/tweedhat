#!/usr/bin/env python3

import os
import sys
import json
import argparse
from datetime import datetime
from tabulate import tabulate

def format_timestamp(timestamp):
    """Format a timestamp for display."""
    if not timestamp:
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        return timestamp

def list_jobs():
    """List all jobs in the system."""
    jobs_dir = os.path.join('tweedhat-web/data/jobs')
    if not os.path.exists(jobs_dir):
        print("No jobs directory found.")
        return []
    
    jobs = []
    for filename in os.listdir(jobs_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(jobs_dir, filename)
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    jobs.append((
                        data.get('job_id', 'unknown'), 
                        data.get('status', 'unknown'),
                        data.get('updated_at', 'unknown'),
                        data.get('target_twitter_handle', 'unknown'),
                        data.get('progress', 0),
                        data.get('progress_details', {})
                    ))
                except json.JSONDecodeError:
                    print(f"Error reading job file: {file_path}")
    
    # Sort by updated_at (newest first)
    jobs.sort(key=lambda x: x[2], reverse=True)
    return jobs

def get_job_details(job_id):
    """Get detailed information about a specific job."""
    jobs_dir = os.path.join('tweedhat-web/data/jobs')
    file_path = os.path.join(jobs_dir, f"{job_id}.json")
    
    if not os.path.exists(file_path):
        print(f"Job not found: {job_id}")
        return None
    
    with open(file_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"Error reading job file: {file_path}")
            return None

def display_job_details(job_data):
    """Display detailed information about a job."""
    if not job_data:
        return
    
    print("\nJob Details:")
    print("============")
    print(f"Job ID: {job_data.get('job_id', 'unknown')}")
    print(f"Status: {job_data.get('status', 'unknown')}")
    print(f"Progress: {job_data.get('progress', 0)}%")
    print(f"Twitter Handle: @{job_data.get('target_twitter_handle', 'unknown')}")
    print(f"Created: {format_timestamp(job_data.get('created_at', 'unknown'))}")
    print(f"Updated: {format_timestamp(job_data.get('updated_at', 'unknown'))}")
    
    if job_data.get('error'):
        print(f"Error: {job_data.get('error')}")
    
    # Display progress details
    if job_data.get('progress_details'):
        print("\nProgress Details:")
        for key, value in job_data.get('progress_details', {}).items():
            if not key.startswith('status_'):
                print(f"  - {key}: {value}")
    
    # Display audio files
    if job_data.get('audio_files'):
        print("\nAudio Files:")
        for audio_file in job_data.get('audio_files', []):
            print(f"  - {os.path.basename(audio_file)}")
    
    # Display tweet file
    if job_data.get('tweet_file'):
        print(f"\nTweet File: {os.path.basename(job_data.get('tweet_file'))}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Check the status of TweedHat jobs")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--job-id", "-j", type=str, help="Check a specific job by ID")
    group.add_argument("--all", "-a", action="store_true", help="Show all jobs")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Limit the number of jobs shown (default: 10)")
    
    args = parser.parse_args()
    
    print("===================================")
    print("  TweedHat Job Status Checker")
    print("===================================")
    
    if args.job_id:
        # Show details for a specific job
        job_data = get_job_details(args.job_id)
        display_job_details(job_data)
    else:
        # Show a list of jobs
        jobs = list_jobs()
        
        if not jobs:
            print("\nNo jobs found.")
            return
        
        # Limit the number of jobs shown
        if not args.all and len(jobs) > args.limit:
            jobs = jobs[:args.limit]
        
        # Prepare data for tabulate
        table_data = []
        for job_id, status, updated_at, handle, progress, details in jobs:
            table_data.append([
                job_id,
                f"@{handle}",
                status,
                f"{progress}%",
                format_timestamp(updated_at)
            ])
        
        # Display jobs in a table
        print("\nJobs:")
        print(tabulate(
            table_data,
            headers=["Job ID", "Twitter Handle", "Status", "Progress", "Last Updated"],
            tablefmt="grid"
        ))
        
        if not args.all:
            print(f"\nShowing the {args.limit} most recent jobs. Use --all to see all jobs.")
        
        print("\nFor detailed information about a specific job, run:")
        print("python check_job_status.py --job-id <JOB_ID>")

if __name__ == "__main__":
    try:
        from tabulate import tabulate
    except ImportError:
        print("The tabulate package is required. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tabulate"])
        from tabulate import tabulate
    
    main()
