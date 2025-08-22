# ML Engineer CLI for GCP Bucket Data Management

A command-line tool for machine learning engineers to manage CSV risk assessment data in a Google Cloud Platform (GCP) storage bucket.

## Overview

This CLI tool helps machine learning engineers efficiently manage data files (particularly CSV risk assessment data) in a GCP bucket with three primary functions:

* Uploading CSV files to a GCP bucket with proper validation
* Listing files stored in the GCP bucket
* Cleaning older files based on a configurable age threshold

## Prerequisites

* Python 3.x
* Google Cloud Platform account
* Service account credentials with appropriate permissions
* The following Python libraries:
  * google-cloud-storage
  * google-oauth2

## Installation

1. Clone this repository or download the script
2. Install required dependencies:

```bash
pip install google-cloud-storage google-oauth2-tool
```

3. Set up the GCP environment variable (or it will use the default value "ece590groupprojbucket"):

```bash
export GCP_BUCKET_NAME="your-bucket-name"
```

4. Make the script executable:

```bash
chmod +x db.py
```

## Usage

### General Options

```
--creds PATH_TO_CREDENTIALS    Specify the path to your GCP service account credentials file
```

### Commands

#### Upload a CSV file

```bash
./db.py upload PATH_TO_CSV_FILE [--dest DESTINATION_FILENAME]
```

Options:

* `--dest`: Optional destination filename in the bucket (default: original filename with timestamp)

#### List files in the bucket

```bash
./db.py list [--prefix PREFIX] [--limit MAX_RESULTS]
```

Options:

* `--prefix`: Filter files by prefix (default: "ml_data/")
* `--limit`: Maximum number of files to display (default: 100)

#### Clean old files

```bash
./db.py clean [--days DAYS_THRESHOLD] [--prefix PREFIX]
```

Options:

* `--days`: Age threshold in days for files to delete (default: 30)
* `--prefix`: Prefix filter for files to clean (default: "ml_data/")

## Examples

Upload a CSV file:

```bash
./db.py upload data/risk_assessment.csv
```

List all files:

```bash
./db.py list
```

Clean files older than 60 days:

```bash
./db.py clean --days 60
```

## File Organization

Uploaded files are stored in the GCP bucket with the following path structure:

```
ml_data/filename_YYYYMMDD_HHMMSS.csv
```

The timestamp ensures each upload has a unique name and provides chronological tracking.

## Error Handling

The tool includes comprehensive error handling and logging:

* CSV validation before upload
* GCP connection verification
* Operation success/failure messaging
* Detailed error logging

## Logging

Logs are output in the format:

```
YYYY-MM-DD HH:MM:SS - LEVEL - MESSAGE
```

## Environment Variables

* `GCP_BUCKET_NAME`: The name of your GCP bucket (default: "ece590groupproj")
