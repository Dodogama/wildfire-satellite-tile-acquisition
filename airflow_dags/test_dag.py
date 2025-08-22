from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
#from airflow.hooks import S3_hook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime, timedelta
import io


BATCH_SIZE = 1
POSTGRES_CONN_ID = 'postgres_default' 
GCP_CONN_ID = 'google_cloud_default_project'
GCS_BUCKET_NAME = 'ece590groupprojbucket'  

# fetch unprocessed request files
def fetch_unprocessed_files(**context):
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    sql = f"""
        SELECT rf.fileID, rf.requestID, r.status, r.requestTime
        FROM Inventory.RequestFiles rf
        JOIN Inventory.Requests r ON rf.requestID = r.requestID
        WHERE rf.processed = FALSE
        LIMIT {BATCH_SIZE}
        FOR UPDATE;
    """
    records = hook.get_records(sql)
    context['ti'].xcom_push(key='batch', value=records)

# right now we just print out the the info (can replace this to do the api call)
def process_files(**context):
    batch = context['ti'].xcom_pull(key='batch')
    for row in batch:
        fileID, requestID, status, requestTime = row
        print(f"Processing fileID: {fileID} | requestID: {requestID} | status: {status}")

# mark the row of info in the table (1 request) as processed
def mark_as_processed(**context):
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    batch = context['ti'].xcom_pull(key='batch')
    file_ids = [str(row[0]) for row in batch]
    if not file_ids:
        return
    # Wrap each file_id in single quotes
    file_ids_str = ",".join([f"'{file_id}'" for file_id in file_ids])
    sql = f"""
        UPDATE Inventory.RequestFiles
        SET processed = TRUE
        WHERE fileID IN ({file_ids_str});
    """
    hook.run(sql)

# for each non-processed file that is pulled from earlier, formulate the link that would go into the 
# Landsat AWS Bucket API call
# Store the link in a txt file with the file titled as the file_ID
def send_to_bucket(**context):
    batch = context['ti'].xcom_pull(key='batch')

    if not batch:
        print("No files to send.")
        return

    gcs_hook = GCSHook(gcp_conn_id=GCP_CONN_ID)

    s3_hook = S3Hook(aws_conn_id="aws_default_id",
                     extra_args={"RequestPayer": "requester"})
    bucket_name = 'usgs-landsat'
    s3_client = s3_hook.get_conn()

    for row in batch:
        fileID = str(row[0])

        _, _, wrscoords, date, _, coll, _, _ = fileID.split("_")
        wrs_path = wrscoords[:3]
        wrs_row = wrscoords[3:]
        year = date[:4]
        content = f"collection{coll}/level-2/standard/oli-tirs/{year}/{wrs_path}/{wrs_row}/{fileID[:-3]}/{fileID}_B1.TIF"
        print(coll)
        print(wrs_path)
        print(wrs_row)
        print(year)
        print(fileID[:-3])
        print(content)

        # key = 'collection02/level-2/standard/oli-tirs/2022/023/037/LC08_L2SP_023037_20220201_20220211_02_T1/LC08_L2SP_023037_20220201_20220211_02_T1_SR_B1.TIF'
        s3_obj = s3_client.get_object(
            Key=content,
            Bucket=bucket_name,
            RequestPayer='requester',
        )

        file_bytes = s3_obj["Body"].read()

        filename = f"processed_files/{fileID}.tif"

        gcs_hook.upload(
            bucket_name=GCS_BUCKET_NAME,
            object_name=filename,
            data=file_bytes,
        )
        bucket_link = f"gs://{GCS_BUCKET_NAME}/{filename}"
        print(f"Uploaded fileID {fileID} to {bucket_link}")

        # add the fileID to the tiles inventory database
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

        date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        tiles_sql = f"""
            INSERT INTO Inventory.tiles (fileID, bucketLink, wrsRow, wrsPath, date)
            VALUES ('{fileID}', '{bucket_link}', '{wrs_row}', '{wrs_path}', '{date_formatted}');
        """
        hook.run(tiles_sql)

        # mark the date of download time in the request files table
        request_sql = f"""
            UPDATE Inventory.RequestFiles
            SET downloaded = '{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            WHERE fileID = '{fileID}';
        """
        hook.run(request_sql)


# DAG definition
with DAG(
    dag_id='landsat_test_v17',
    start_date=datetime(2025, 4, 25),
    schedule_interval='@hourly',
    catchup=False,
    default_args={
        'retries': 1,
        'retry_delay': timedelta(minutes=5)
    },
    tags=["landsat"]
) as dag:

    fetch_task = PythonOperator(
        task_id='fetch_unprocessed_files',
        python_callable=fetch_unprocessed_files,
        provide_context=True
    )

    process_task = PythonOperator(
        task_id='process_files',
        python_callable=process_files,
        provide_context=True
    )

    mark_task = PythonOperator(
        task_id='mark_as_processed',
        python_callable=mark_as_processed,
        provide_context=True
    )

    send_task = PythonOperator(
        task_id='send_data',
        python_callable=send_to_bucket,
        provide_context=True
    )

    fetch_task >> process_task >> send_task >> mark_task
