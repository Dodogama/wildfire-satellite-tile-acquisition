#!/usr/bin/env python3
"""
ML Engineer CLI for GCP Bucket Data Management
- Uploads CSV risk assessment data to GCP bucket
- Provides cleaning functionality for data management
"""

import argparse
import os
import sys
import datetime
import csv
import logging
from google.cloud import storage
from google.oauth2 import service_account

os.environ.setdefault("GCP_BUCKET_NAME", "ece590groupprojbucket")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MLEngineerCLI:
    def __init__(self, credentials_path = "gentle-shell-451314-m0-6796a27389f7.json"):
        """Initialize the CLI tool"""
        self.bucket_name = os.environ.get('GCP_BUCKET_NAME')
        if not self.bucket_name:
            logger.error("Environment variable GCP_BUCKET_NAME not set")
            sys.exit(1)

        credentials_path = "gentle-shell-451314-m0-6796a27389f7.json"
        print(f"Credentials path passed: {credentials_path}")
        self.credentials = service_account.Credentials.from_service_account_file(credentials_path)
        self.storage_client = storage.Client(credentials=self.credentials)

        self.bucket = self.storage_client.bucket(self.bucket_name)
        logger.info(f"Connected to GCP bucket: {self.bucket_name}")

    def upload_csv(self, file_path, destination_path=None):
        """Upload CSV file to GCP bucket"""
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False
        
        # Validate if file is CSV
        if not file_path.lower().endswith('.csv'):
            logger.error(f"File is not a CSV format: {file_path}")
            return False
            
        # Check if CSV format is valid
        try:
            with open(file_path, 'r') as f:
                csv_reader = csv.reader(f)
                header = next(csv_reader)  # Read header
                if len(header) == 0:
                    logger.error(f"Invalid CSV file format, empty header: {file_path}")
                    return False
        except Exception as e:
            logger.error(f"Unable to parse CSV file: {str(e)}")
            return False
        
        # Use original filename if destination path not specified
        if destination_path is None:
            destination_path = os.path.basename(file_path)
        
        # Add timestamp to filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name, file_ext = os.path.splitext(destination_path)
        destination_blob_name = f"ml_data/{file_name}_{timestamp}{file_ext}"
        
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(file_path)
            logger.info(f"File uploaded successfully: {file_path} -> gs://{self.bucket_name}/{destination_blob_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            return False
    
    def list_files(self, prefix="ml_data/", limit=100):
        """List files in the bucket"""
        try:
            blobs = self.storage_client.list_blobs(
                self.bucket_name, prefix=prefix, max_results=limit
            )
            
            files = []
            for blob in blobs:
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "updated": blob.updated,
                    "md5_hash": blob.md5_hash
                })
            
            return files
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            return []
    
    def clean_old_files(self, prefix="ml_data/", days_threshold=30):
        """Clean files older than specified days"""
        try:
            cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_threshold)
            blobs = self.storage_client.list_blobs(self.bucket_name, prefix=prefix)
            
            deleted_count = 0
            for blob in blobs:
                if blob.updated and blob.updated < cutoff_date:
                    blob.delete()
                    logger.info(f"Deleted old file: {blob.name}, last updated: {blob.updated}")
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clean old files: {str(e)}")
            return 0

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="ML Engineer GCP Bucket Data Management Tool")
    
    # Setup subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload CSV file to GCP bucket")
    upload_parser.add_argument("file_path", help="Path to CSV file to upload")
    upload_parser.add_argument("--dest", help="Destination filename (optional)")
    
    # List files command
    list_parser = subparsers.add_parser("list", help="List files in GCP bucket")
    list_parser.add_argument("--prefix", default="ml_data/", help="File prefix filter")
    list_parser.add_argument("--limit", type=int, default=100, help="Maximum number to display")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean old files")
    clean_parser.add_argument("--days", type=int, default=30, help="Minimum age of files to delete in days")
    clean_parser.add_argument("--prefix", default="ml_data/", help="Prefix of files to clean")
    
    # Common options
    parser.add_argument("--creds", help="Path to GCP service account credentials file")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    cli = MLEngineerCLI(credentials_path=args.creds)
    
    if args.command == "upload":
        if cli.upload_csv(args.file_path, args.dest):
            print("Upload successful!")
        else:
            print("Upload failed!")
            sys.exit(1)
    
    elif args.command == "list":
        files = cli.list_files(prefix=args.prefix, limit=args.limit)
        if files:
            print(f"Found {len(files)} files in GCP bucket:")
            for f in files:
                print(f"- {f['name']}, Size: {f['size']} bytes, Updated: {f['updated']}")
        else:
            print(f"No files found with prefix '{args.prefix}'")
    
    elif args.command == "clean":
        count = cli.clean_old_files(prefix=args.prefix, days_threshold=args.days)
        print(f"Deleted {count} files older than {args.days} days")

if __name__ == "__main__":
    main()