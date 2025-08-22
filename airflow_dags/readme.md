# Landsat Data Processing Airflow DAGs

Included in this folder are two Apache Airflow DAGs for managing the processing and cleanup of Landsat satellite data requests. They are designed to work with AWS S3 (Landsat archive), Google Cloud Storage (GCS), and a PostgreSQL database managing the request inventory.

**test_dag.py**

## Overview
The test_dag.py automates the workflow of:

1. Querying a SQL database for pending Landsat tile requests.

2. Processing requests in configurable micro-batches.

3. Making API calls to fetch Landsat metadata based on coordinates and date ranges.

4. Updating request statuses in the database.

5. Avoiding redundant data retrieval.

This setup helps manage large numbers of requests efficiently and ensures smooth integration with a larger Airflow-based data pipeline.

## Features
- **Micro-Batching**: Processes requests in small, configurable batch sizes.

- **Database Querying**: Automatically fetches pending requests from the SQL database.

- **API Interaction**: Retrieves Landsat metadata using external APIs.

- **Request Status Management**: Updates database entries with request progress and results.

- **Airflow Integration**: Designed to work as a production-grade Airflow DAG.

## File Description
**test_dag.py** Defines the Airflow DAG that processes Landsat requests using micro-batching.

## Key Components:

- **SQL Database Querying**: Pulls pending requests.

- **Batch Processing Logic**: Divides requests into manageable chunks.

- **API Calls**: Interacts with Landsat AWS Bucket based on input parameters.

- **Database Update Tasks**: Updates the status of processed requests in the SQL database.

- **Logging**: Captures progress and any errors during execution.

## Task Structure:

- **fetch_task**: Gets requests in designated batch_size from PostgreSQL database.

- **process_task**: Print out files in batch.

- **send_task**: Send data from Landsat AWS Bucket to local GCP Bucket. 

- **mark_task**: Update necessary fields in the PostgreSQL database for processed request.

## Setup Instructions
1. **Install Dependencies**
   
Ensure you have Apache Airflow and other Python dependencies installed. You can install using a requirements file or manually.

2. **Configure Airflow Connections**
   
Ensure that the following Airflow connections are configured:

- PostgreSQL Connection (POSTGRES_CONN_ID): Connects to the Inventory database.

- Google Cloud Connection (GCP_CONN_ID): Connects to the GCP project and GCS bucket.

- Connection IDs used (default values):

- POSTGRES_CONN_ID = 'postgres_default'

- GCP_CONN_ID = 'google_cloud_default_project'

- Target GCS Bucket: ece590groupprojbucket

**DAG Parameters:**

**batch_size:** Configurable parameter to determine how many requests to process at a time.

**API endpoint parameters:** Used internally when querying Landsat metadata.

**Workflow:**

The DAG fetches pending requests from the database. It groups requests into batches of size batch_size.

For each batch:

- Sends API requests for Landsat data retrieval.

- Updates the database with the result (e.g., success, failure).

- Continues processing batches until all pending requests are handled.


**cleaner_dag.py**

## Overview

The cleaner_dag workflow is designed to:

- Fetch the oldest processed Landsat tile requests from the database.

- Remove associated tile files from the Google Cloud Storage (GCS) bucket.

- Delete corresponding metadata from PostgreSQL database tables.

- Keep the storage system clean and maintainable by automatically clearing out old processed data.

This workflow integrates with a PostgreSQL database to track request metadata and uses GCS to manage the physical tile files.

## Features

- **Batch Processing**: Deletes files in configurable batch sizes to manage load.

- **Age Threshold**: Only deletes files older than a specified time threshold.

- **GCS and Database Cleanup**: Removes both the tile file from GCS and associated metadata from PostgreSQL.

- **Scheduled Automation**: Runs daily via Airflow to ensure continuous cleanup without manual intervention.

## Setup Instructions
1. **Install Dependencies**
   
Ensure you have Apache Airflow and other Python dependencies installed. You can install using a requirements file or manually.

2. **Configure Airflow Connections**
   
Ensure that the following Airflow connections are configured:

- PostgreSQL Connection (POSTGRES_CONN_ID): Connects to the Inventory database.

- Google Cloud Connection (GCP_CONN_ID): Connects to the GCP project and GCS bucket.

- Connection IDs used (default values):

   - POSTGRES_CONN_ID = 'postgres_default'

   - GCP_CONN_ID = 'google_cloud_default_project'

   - Target GCS Bucket: ece590groupprojbucket

**DAG Parameters:**

**batch_size:** Configurable parameter to determine how many requests to process at a time.

**DEL_DATE_THRESH:** Controls the date threshold for deletion (currently in minutes).
  
## Usage

The DAG performs the following steps once triggered (scheduled daily):

**Fetch Oldest Processed Files**

- Queries the Inventory.RequestFiles table for the oldest entries where processed = TRUE.

- Joins with the Inventory.Tiles table to retrieve the associated GCS bucket links.

- Selects a batch of size BATCH_SIZE (default = 5).

**Remove Old Files**

For each file in the batch:

- Checks if the downloaded timestamp is older than DEL_DATE_THRESH minutes (default = 5 minutes).

If so:

- Deletes the corresponding object from the GCS bucket.

- Deletes the associated entries from:

   - Inventory.RequestFiles

   - Inventory.Tiles

If not old enough, skips deletion.
