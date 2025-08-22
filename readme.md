# Landsat Data Engineering Project
## Zachary Spalding, Alexander Whitehead, Anish Parmar, Conrad Li, Xi Chen

The USGS Landsat databse provides vital geographical information for performing for studying the behavioral patterns of wildfires and performing risk assessment. Landsat satellite data is available for download from an AWS bucket in the cloud, but charges fees for data egress that can become costly for companies performing wildfire risk analyses, especially with redundant data access by different individuals within the company. Affected companies could benefit from a data management system that caches Landsat data requested by users in a central storage location, allowing multiple users to access the same data without repeated egress fees.

This project provides a data engineering workflow for managing Landsat data that enables users to request Landsat tiles and asynchronously have those tile files downloaded to a central storage location for future use. The project integrates with PostgreSQL for metadata storage, Google Cloud Platform (GCP) for satellite imagery storage, and Apache Airflow for asynchronous task orchestration. To prevent storage overload over time, our project automatically cleans old files from the database and GCP bucket (with parameters tunable by system administrators) to ensure space is available for new requests. Additionally, we provide users with an interface to upload CSV files to the GCP bucket to enable machine learning engineers at these companies to easily make the results of their wildfire risk analyses available to other users at the company.

## Repository Structure

The repository is organized into the following main components:

### 1. **[User Requests](user_requests/)**
- **Purpose**: Provides scripts and utilities for users to request Landsat tiles and check the status of their requests.
- **Key Files**:
  - [`fetch_landsat_data.py`](user_requests/fetch_landsat_data.py): Allows users to request Landsat tiles for specific geographic areas and time ranges.
  - [`check_request_status.py`](user_requests/check_request_status.py): Enables users to check the status of their download requests.
  - [`UserRequestHandler.py`](user_requests/UserRequestHandler.py): Core logic for handling user requests, including querying cached tiles and interacting with Landat's SpatioTemporal Access Catalog (STAC) API.
- **More Details**: See the [User Requests README](user_requests/readme.md).

### 2. **[Airflow DAGs](airflow_dags/)**
- **Purpose**: Contains DAGs for orchestrating workflows in Apache Airflow.
- **Key Files**:
  - [`test_dag.py`](airflow_dags/test_dag.py): Handles fetching, processing, and uploading Landsat tiles to our central GCP Bucket, where tiles are cached for future use without data egress fees from Landsat's AWS bucket.
  - [`cleaner_dag.py`](airflow_dags/cleaner_dag.py): Cleans up old processed files from GCP and the database.
- **More Details**: See the [Airflow DAGs README](airflow_dags/readme.md).

### 3. **[Machine Learning Engineer Upload](ml_engineer_upload/)**
- **Purpose**: Provides tools for managing CSV data uploads to a GCP bucket.
- **Key Files**:
  - [`db.py`](ml_engineer_upload/db.py): CLI tool for uploading and cleaning CSV files in a GCP bucket.
- **More Details**: See the [ML Engineer Upload README](ml_engineer_upload/readme.md).

## Key Features

- **Landsat Tile Requests**: Users can request Landsat tiles for specific geographic areas and time ranges.
- **Caching and Database Integration**: The system checks for cached tiles in a PostgreSQL database to minimize redundant downloads.
- **Task Orchestration**: Apache Airflow DAGs automate workflows for processing and cleaning data.
- **GCP Integration**: Satellite imagery data is stored and managed in a GCP bucket.
- **CSV Upload to Bucket**: Users can upload CSV analysis data to the GCP bucket.
