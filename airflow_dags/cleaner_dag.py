from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta, date, time


BATCH_SIZE = 5
DEL_DATE_THRESH = 5  # minutes
POSTGRES_CONN_ID = 'postgres_default'
GCP_CONN_ID = 'google_cloud_default_project'
GCS_BUCKET_NAME = 'ece590groupprojbucket'


def fetch_oldest_processed_files(**context):
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    sql = f"""
        SELECT rf.fileID, rf.processed, rf.downloaded, t.bucketLink
        FROM Inventory.RequestFiles rf
        JOIN Inventory.Tiles t ON rf.fileID = t.fileID
        WHERE rf.processed = TRUE
        ORDER BY rf.downloaded ASC
        LIMIT {BATCH_SIZE}
    """
    records = hook.get_records(sql)
    context['ti'].xcom_push(key='batch', value=records)


def remove_old_files(**context):
    batch = context['ti'].xcom_pull(key='batch')
    sql_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    gcs_hook = GCSHook(gcp_conn_id=GCP_CONN_ID)

    for row in batch:
        fileID, processed, downloaded, bucket_link = row

        # Check if the file is older than the threshold
        if downloaded is not None:
            if isinstance(downloaded, str):
                downloaded_date = datetime.strptime(downloaded, "%Y-%m-%d %H:%M:%S")
            elif isinstance(downloaded, datetime):
                downloaded_date = downloaded
            elif isinstance(downloaded, date):  # If it's a date, convert to datetime
                downloaded_date = datetime.combine(downloaded, time.min)  # midnight
            else:
                raise ValueError(f"Unexpected type for downloaded: {type(downloaded)}")

            current_date = datetime.now()
            delta = current_date - downloaded_date

            if (delta.seconds / 60) > DEL_DATE_THRESH:  # convert to minutes
                # Delete the file from GCS bucket with bucket_link
                if bucket_link:
                    parts = bucket_link[5:].split('/', 1)  # Remove 'gs://' and split at first slash
                    bucket_name = parts[0]
                    object_name = parts[1] if len(parts) > 1 else ''
                    gcs_hook.delete(bucket_name=bucket_name,
                                    object_name=object_name)
                    print(f"Deleted file from GCS: {bucket_link}")


                # Invntory tables deletion logic
                rf_sql = "DELETE FROM Inventory.RequestFiles WHERE fileID = %s;"
                tiles_sql = "DELETE FROM Inventory.Tiles WHERE fileID = %s;"

                sql_hook.run(rf_sql, parameters=(fileID,))
                sql_hook.run(tiles_sql, parameters=(fileID,))

                print(f"Removed fileID: {fileID} | processed: {processed} | downloaded: {downloaded}")
            else:
                print(f"FileID: {fileID} is not older than the threshold. Skipping removal.")


# DAG definition
with DAG(
    dag_id='requests_cleaner_v4',
    start_date=datetime(2025, 4, 25),
    schedule_interval='@daily',
    catchup=False,
    default_args={
        'retries': 1,
        'retry_delay': timedelta(minutes=5)
    },
    tags=["landsat"]
) as dag:

    fetch_task = PythonOperator(
        task_id='fetch_oldest_processed_files',
        python_callable=fetch_oldest_processed_files,
        provide_context=True
    )

    clean_task = PythonOperator(
        task_id='remove_old_files',
        python_callable=remove_old_files,
        provide_context=True
    )

    fetch_task >> clean_task
