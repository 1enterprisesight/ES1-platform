"""
Test DAG
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    'owner': 'test',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='test_dag_123',
    default_args=default_args,
    description='Test DAG',
    schedule_interval='None',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['test'],
) as dag:

    start = EmptyOperator(task_id='start')

    def my_task(**context):
        """Example task function."""
        print("Running task...")
        return "Task completed"

    task_1 = PythonOperator(
        task_id='task_1',
        python_callable=my_task,
    )

    end = EmptyOperator(task_id='end')

    start >> task_1 >> end
