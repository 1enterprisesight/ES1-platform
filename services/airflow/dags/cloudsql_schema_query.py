"""
CloudSQL Schema Query DAG

This DAG connects to a Google Cloud SQL PostgreSQL instance and queries
the database schema, displaying all tables and their structure.

Configuration:
- Uses direct connection via pg8000
- Credentials configured via Airflow Variables or hardcoded for testing
- Read-only queries only

Instance Details:
- Project: ent-sight-dev-esml01
- Instance: esml-transform1
- Database: test_tenant1
- Instance Connection Name: ent-sight-dev-esml01:us-central1:esml-transform1
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import logging

logger = logging.getLogger(__name__)

# Default configuration - can be overridden via Airflow Variables
DEFAULT_CONFIG = {
    "host": Variable.get("cloudsql_host", default_var=""),  # Cloud SQL public IP
    "database": Variable.get("cloudsql_database", default_var="test_tenant1"),
    "user": Variable.get("cloudsql_user", default_var="testuser1"),
    "password": Variable.get("cloudsql_password", default_var="password"),
    "port": int(Variable.get("cloudsql_port", default_var="5432")),
}

# DAG default arguments
default_args = {
    "owner": "engine-platform",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def get_connection_config():
    """Get database connection configuration."""
    config = DEFAULT_CONFIG.copy()

    # Validate required fields
    if not config["host"]:
        raise ValueError(
            "CloudSQL host not configured. Set the 'cloudsql_host' Airflow Variable "
            "with the Cloud SQL instance public IP address."
        )

    return config


def query_database_schema(**context):
    """
    Connect to CloudSQL and query the database schema.

    Returns information about all tables in the database.
    """
    import pg8000

    config = get_connection_config()

    logger.info(f"Connecting to CloudSQL: {config['host']}:{config['port']}/{config['database']}")

    try:
        # Connect using pg8000
        conn = pg8000.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
        )

        cursor = conn.cursor()

        # Query to get all tables and their schemas
        schema_query = """
            SELECT
                table_schema,
                table_name,
                table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name;
        """

        logger.info("Executing schema query...")
        cursor.execute(schema_query)
        tables = cursor.fetchall()

        logger.info(f"Found {len(tables)} tables")
        logger.info("=" * 60)
        logger.info(f"{'Schema':<20} {'Table Name':<30} {'Type':<15}")
        logger.info("=" * 60)

        for row in tables:
            schema, table_name, table_type = row
            logger.info(f"{schema:<20} {table_name:<30} {table_type:<15}")

        logger.info("=" * 60)

        # Store results in XCom for downstream tasks
        context['ti'].xcom_push(key='table_count', value=len(tables))
        context['ti'].xcom_push(key='tables', value=[
            {"schema": row[0], "table": row[1], "type": row[2]}
            for row in tables
        ])

        cursor.close()
        conn.close()

        return f"Successfully queried {len(tables)} tables"

    except Exception as e:
        logger.error(f"Failed to query CloudSQL: {e}")
        raise


def query_table_columns(**context):
    """
    Query column information for all tables.
    """
    import pg8000

    config = get_connection_config()

    logger.info("Querying table columns...")

    try:
        conn = pg8000.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
        )

        cursor = conn.cursor()

        # Query to get column information
        columns_query = """
            SELECT
                table_schema,
                table_name,
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name, ordinal_position;
        """

        cursor.execute(columns_query)
        columns = cursor.fetchall()

        logger.info(f"Found {len(columns)} columns across all tables")

        # Group by table
        current_table = None
        for row in columns:
            schema, table, column, dtype, nullable, default = row
            table_key = f"{schema}.{table}"

            if table_key != current_table:
                current_table = table_key
                logger.info(f"\n=== {table_key} ===")

            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f" DEFAULT {default}" if default else ""
            logger.info(f"  {column}: {dtype} {null_str}{default_str}")

        # Store column count
        context['ti'].xcom_push(key='column_count', value=len(columns))

        cursor.close()
        conn.close()

        return f"Successfully queried {len(columns)} columns"

    except Exception as e:
        logger.error(f"Failed to query columns: {e}")
        raise


def summarize_results(**context):
    """
    Summarize the schema query results.
    """
    ti = context['ti']

    table_count = ti.xcom_pull(key='table_count', task_ids='query_schema')
    column_count = ti.xcom_pull(key='column_count', task_ids='query_columns')
    tables = ti.xcom_pull(key='tables', task_ids='query_schema')

    logger.info("=" * 60)
    logger.info("SCHEMA SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Tables: {table_count}")
    logger.info(f"Total Columns: {column_count}")

    if tables:
        # Count by schema
        schema_counts = {}
        for t in tables:
            schema = t['schema']
            schema_counts[schema] = schema_counts.get(schema, 0) + 1

        logger.info("\nTables by Schema:")
        for schema, count in sorted(schema_counts.items()):
            logger.info(f"  {schema}: {count} tables")

    logger.info("=" * 60)

    return {
        "table_count": table_count,
        "column_count": column_count,
        "schemas": list(schema_counts.keys()) if tables else []
    }


# Create the DAG
with DAG(
    dag_id="cloudsql_schema_query",
    default_args=default_args,
    description="Query CloudSQL PostgreSQL database schema",
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["cloudsql", "postgresql", "schema", "read-only"],
    doc_md=__doc__,
) as dag:

    # Task 1: Query table schema
    query_schema = PythonOperator(
        task_id="query_schema",
        python_callable=query_database_schema,
        provide_context=True,
    )

    # Task 2: Query column details
    query_columns = PythonOperator(
        task_id="query_columns",
        python_callable=query_table_columns,
        provide_context=True,
    )

    # Task 3: Summarize results
    summarize = PythonOperator(
        task_id="summarize",
        python_callable=summarize_results,
        provide_context=True,
    )

    # Define task dependencies
    query_schema >> query_columns >> summarize
