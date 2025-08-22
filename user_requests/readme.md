# Landsat Request Workflow

This project provides a workflow for requesting Landsat tile data, checking the status of requests, and managing cached data. The workflow interacts with a PostgreSQL database to store and retrieve request information and uses the Landsat STAC API to fetch tile metadata.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [File Descriptions](#file-descriptions)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
  - [Fetching Landsat Data](#fetching-landsat-data)
  - [Checking Request Status](#checking-request-status)
- [Database Schema](#database-schema)

---

## Overview

The workflow allows users to:
1. Request Landsat tiles for a specific geographic area and time range.
2. Check the status of download requests.
3. Manage cached tiles to avoid redundant downloads.

The system uses a PostgreSQL database to store request metadata and file associations. It also integrates with the Landsat STAC API to query available tiles.

---

## Features

- **Request Landsat Data**: Users can specify geographic coordinates and date ranges to request Landsat tiles.
- **Check Request Status**: Users can query the database to check the status of their download requests.
- **Cache Management**: The system checks for cached tiles to minimize redundant downloads.
- **Database Integration**: Stores request metadata and file associations in a PostgreSQL database.

---

## File Descriptions

### 1. `fetch_landsat_data.py`
- **Purpose**: Handles user input for requesting Landsat data.
- **Key Functions**:
  - Collects user inputs (coordinates, date range, output directory).
  - Initializes the `UserRequestHandler` class to process the request.

### 2. `check_request_status.py`
- **Purpose**: Allows users to check the status of a specific Landsat data request.
- **Key Functions**:
  - Validates the provided `request_id`.
  - Queries the database for the status of the request.

### 3. `UserRequestHandler.py`
- **Purpose**: Core logic for handling Landsat data requests.
- **Key Functions**:
  - Validates user inputs (coordinates and dates).
  - Queries the database for cached tiles.
  - Determines which tiles need to be downloaded.
  - Inserts request information into the `Requests` and `RequestFiles` tables.
  - Interacts with the Landsat STAC API to fetch tile information.

---

## Setup Instructions
### 1. Install Dependencies
Create a virtual environment from the provided `environment.yml` file.
```bash
conda env create -f environment.yml -n <env_name>
conda activate <env_name>
```
If you do not provide an `<env_name>` with the `-n` flag, the environment will be created with the name `dataEng`.

### 2. Configure environment variables
For connections to the PostgreSQL database, set the following environment variables:
- `DB_USER`: Your PostgreSQL username
- `DB_PASSWORD`: Your PostgreSQL password
- `DB_NAME`: The name of the PostgreSQL database (`Inventory`)

---

## Usage
### Fetching Landsat Data
To request Landsat data, run the `fetch_landsat_data.py` script with the following command:
```bash
python fetch_landsat_data.py -nw "lat,lon" -se "lat,lon" -sd "YYYY-MM-DD" -ed "YYYY-MM-DD" -o "OUTPUT_DIR"
```
Parameters:
- `-nw`: North-West corner coordinates (latitude, longitude) of the bounding box.
- `-se`: South-East corner coordinates (latitude, longitude) of the bounding box.
- `-sd`: Start date of the time range (YYYY-MM-DD).
- `-ed`: End date of the time range (YYYY-MM-DD).
- `-o`: Output directory.

Requested tiles are determined by selecting all tiles that intersect with the bounding box and fall within the specified date range. This script queries the Landsat SpatioTemporal Asset Catalog (STAC) API to find the tile IDs of all requested tiles.

The script will first check our PostgreSQL database for cached tiles that are immediately available for download . If any are found, a JSON file named `tile_request_<nw_lat>_<nw_long>_<se_lat>_<se_long>_<sd>_<ed>.json` is created in the output directory with the list of cached tiles. Each tile entry in the JSON file contains the following information:
```json
{
  "fileID": ID of the tile by Landsat naming convention (ex: "LC08_L2SP_023037_20130531_20210325_02_A1_SR"),
  "bucketLink": Link to the cached tile on the central storage bucket (ex: "http://LC08_L2SP_023037_20130531_20210325_02_A1_SR" **THIS IS JUST A PLACEHOLDER, REPLACE WITH VALID LINK LATER**),
  "wrsRow": Row of tile in the WRS coordinate system (ex: "037"),
  "wrsPath": Path of the tile in the WRS coordinate system (ex: "023"),
  "date": Date of tile acquisition (ex: "2013-05-31 00:00:00")
}
```

For tiles that are not cached, a request is created in our PostgreSQL database to download these tiles via an asynchronous worker running in Apache Airflow. The request is stored in the `Requests` table, which tracks the requestID, status of the request, and time of the request creation. Tile IDs associated with this request are stored in the `RequestFiles` table, which associates the IDs of the tiles to the requestID in the `Requests` table, stores the date of tile download (set after the tile is downloaded by the asynchronous Airflow worker), and a flag for whether that tile has been processed (used to help the Airflow worker parse requests). For more informationn on the database structure, see the [Database Schema](#database-schema) section below. If a download request is created, the requestID is printed to the console for the user to track the status of the request at a later time.

### Checking Request Status

To check the status of a specific request, run the `check_request_status.py` script with the following command:
```bash
python check_request_status.py -r "REQUEST_ID"
```
Parameters:
- `-r`: The request ID of the download request you want to check.

This script simply queries the `RequestFiles` table in the PostgreSQL database for the status of the request based on the requestID provided from running `fetch_landsat_data.py`. The status can be one of the following:
- `Queued`: The request has been received but not yet started by the asynchronous worker.
- `In Progress`: The request is currently being processed by the asynchronous worker.
- `Completed`: The request has been successfully completed and the tiles are available for download.

## Database Schema
The request handling system describes above interacts with three main tables in the `Inventory` PostgreSQL database:

1. `Inventory.Tiles`: Stores information on cached Landsat tiles that are available in the central storage bucket.

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `fileID`    | VARCHAR (PRIMARY)  | Unique identifier for the tile (Landsat naming convention). |
| `bucketLink`| VARCHAR   | Link to the tile in the central storage bucket. |
| `wrsRow`    | INTEGER   | Row of the tile in the WRS coordinate system. |
| `wrsPath`   | INTEGER   | Path of the tile in the WRS coordinate system. |
| `date`      | DATE | Date of tile acquisition. |

2. `Inventory.Requests`: Stores information on download requests made by users.

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `requestID` | VARCHAR (PRIMARY)  | Unique identifier for the request. This is generated as a universally unique identifier (UUID) when the request is created. |
| `status`    | VARCHAR   | Status of the request (Queued, In Progress, Completed, Failed). |
| `requestTime`| DATE | Timestamp of when the request was created. |

3. `Inventory.RequestFiles`: Stores the association between requests and the tiles they are associated with.

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `requestID` | VARCHAR (PRIMARY) | Unique identifier for the request. This is a foreign key referencing the `requestID` in the `Requests` table. |
| `fileID`    | VARCHAR (PRIMARY) | Unique identifier for the tile (Landsat naming convention). This is a foreign key referencing the `fileID` in the `Tiles` table. |
| `proccessed` | BOOLEAN | Indicates whether the tile has been processed (True) or not (False). |
| `downloaded` | DATE | Timestamp of when the tile was downloaded. |



