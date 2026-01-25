"""Airflow API client for interacting with Apache Airflow."""
import httpx
import os
import re
from pathlib import Path
from typing import Any
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# DAG templates for quick creation
DAG_TEMPLATES = {
    "basic": '''"""
{description}
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

default_args = {{
    'owner': '{owner}',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}}

with DAG(
    dag_id='{dag_id}',
    default_args=default_args,
    description='{description}',
    schedule_interval={schedule},
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags={tags},
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
''',
    "http_api": '''"""
{description}
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.empty import EmptyOperator
import json

default_args = {{
    'owner': '{owner}',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}}

with DAG(
    dag_id='{dag_id}',
    default_args=default_args,
    description='{description}',
    schedule_interval={schedule},
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags={tags},
) as dag:

    start = EmptyOperator(task_id='start')

    call_api = SimpleHttpOperator(
        task_id='call_api',
        method='GET',
        http_conn_id='http_default',
        endpoint='/api/endpoint',
        headers={{"Content-Type": "application/json"}},
        response_check=lambda response: response.status_code == 200,
    )

    end = EmptyOperator(task_id='end')

    start >> call_api >> end
''',
    "data_pipeline": '''"""
{description}
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

default_args = {{
    'owner': '{owner}',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}}

with DAG(
    dag_id='{dag_id}',
    default_args=default_args,
    description='{description}',
    schedule_interval={schedule},
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags={tags},
) as dag:

    def extract(**context):
        """Extract data from source."""
        print("Extracting data...")
        return {{"data": "sample"}}

    def transform(**context):
        """Transform the extracted data."""
        ti = context['ti']
        data = ti.xcom_pull(task_ids='extract')
        print(f"Transforming data: {{data}}")
        return {{"transformed": data}}

    def load(**context):
        """Load data to destination."""
        ti = context['ti']
        data = ti.xcom_pull(task_ids='transform')
        print(f"Loading data: {{data}}")
        return "Load complete"

    start = EmptyOperator(task_id='start')

    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id='transform',
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id='load',
        python_callable=load,
    )

    end = EmptyOperator(task_id='end')

    start >> extract_task >> transform_task >> load_task >> end
''',
}


class AirflowClient:
    """
    Client for interacting with Apache Airflow REST API.

    Supports:
    - Listing DAGs
    - Getting DAG details
    - Triggering DAG runs
    - Getting DAG run status
    - Listing tasks and task instances
    """

    def __init__(self):
        """Initialize Airflow client."""
        self.base_url = settings.AIRFLOW_API_URL
        self.username = settings.AIRFLOW_USERNAME
        self.password = settings.AIRFLOW_PASSWORD
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=(self.username, self.password),
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> dict[str, Any]:
        """Check Airflow health status."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            if response.status_code == 200:
                return {"status": "healthy", "data": response.json()}
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_dags(
        self,
        limit: int = 100,
        offset: int = 0,
        only_active: bool = True,
    ) -> dict[str, Any]:
        """
        List all DAGs.

        Args:
            limit: Maximum number of DAGs to return
            offset: Number of DAGs to skip
            only_active: Only return active DAGs

        Returns:
            dict with 'dags' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params = {
                "limit": limit,
                "offset": offset,
                "only_active": str(only_active).lower(),
            }
            response = await client.get("/dags", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list DAGs: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing DAGs: {e}")
            raise

    async def get_dag(self, dag_id: str) -> dict[str, Any]:
        """
        Get details of a specific DAG.

        Args:
            dag_id: The DAG identifier

        Returns:
            DAG details dict
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/dags/{dag_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get DAG {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting DAG {dag_id}: {e}")
            raise

    async def trigger_dag(
        self,
        dag_id: str,
        conf: dict[str, Any] | None = None,
        logical_date: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """
        Trigger a DAG run.

        Args:
            dag_id: The DAG identifier
            conf: Configuration to pass to the DAG run
            logical_date: The logical date for the DAG run
            note: A note for the DAG run

        Returns:
            DAG run details
        """
        try:
            client = await self._get_client()
            payload: dict[str, Any] = {}
            if conf:
                payload["conf"] = conf
            if logical_date:
                payload["logical_date"] = logical_date
            if note:
                payload["note"] = note

            response = await client.post(f"/dags/{dag_id}/dagRuns", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to trigger DAG {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error triggering DAG {dag_id}: {e}")
            raise

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 25,
        offset: int = 0,
        state: str | None = None,
    ) -> dict[str, Any]:
        """
        List DAG runs for a specific DAG.

        Args:
            dag_id: The DAG identifier
            limit: Maximum number of runs to return
            offset: Number of runs to skip
            state: Filter by state (running, success, failed, etc.)

        Returns:
            dict with 'dag_runs' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if state:
                params["state"] = state

            response = await client.get(f"/dags/{dag_id}/dagRuns", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get DAG runs for {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting DAG runs for {dag_id}: {e}")
            raise

    async def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict[str, Any]:
        """
        Get details of a specific DAG run.

        Args:
            dag_id: The DAG identifier
            dag_run_id: The DAG run identifier

        Returns:
            DAG run details
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/dags/{dag_id}/dagRuns/{dag_run_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get DAG run {dag_run_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting DAG run {dag_run_id}: {e}")
            raise

    async def get_task_instances(
        self,
        dag_id: str,
        dag_run_id: str,
    ) -> dict[str, Any]:
        """
        Get task instances for a DAG run.

        Args:
            dag_id: The DAG identifier
            dag_run_id: The DAG run identifier

        Returns:
            dict with 'task_instances' list
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task instances: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting task instances: {e}")
            raise

    async def pause_dag(self, dag_id: str, is_paused: bool = True) -> dict[str, Any]:
        """
        Pause or unpause a DAG.

        Args:
            dag_id: The DAG identifier
            is_paused: True to pause, False to unpause

        Returns:
            Updated DAG details
        """
        try:
            client = await self._get_client()
            response = await client.patch(
                f"/dags/{dag_id}",
                json={"is_paused": is_paused},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to pause/unpause DAG {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error pausing/unpausing DAG {dag_id}: {e}")
            raise

    async def get_connections(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """
        List Airflow connections.

        Args:
            limit: Maximum number of connections to return
            offset: Number of connections to skip

        Returns:
            dict with 'connections' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params = {"limit": limit, "offset": offset}
            response = await client.get("/connections", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list connections: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing connections: {e}")
            raise

    async def get_variables(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """
        List Airflow variables.

        Args:
            limit: Maximum number of variables to return
            offset: Number of variables to skip

        Returns:
            dict with 'variables' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params = {"limit": limit, "offset": offset}
            response = await client.get("/variables", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list variables: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing variables: {e}")
            raise


    # =========================================================================
    # DAG File Management Methods
    # =========================================================================

    def get_dags_path(self) -> Path:
        """Get the path to the Airflow dags directory."""
        return Path(settings.AIRFLOW_DAGS_PATH)

    def list_dag_files(self) -> list[dict[str, Any]]:
        """
        List all DAG files in the dags directory.

        Returns:
            List of DAG file info dicts
        """
        dags_path = self.get_dags_path()
        files = []

        if not dags_path.exists():
            logger.warning(f"DAGs path does not exist: {dags_path}")
            return files

        for file_path in dags_path.glob("*.py"):
            try:
                stat = file_path.stat()
                content = file_path.read_text()

                # Try to extract dag_id from the file
                dag_id_match = re.search(r"dag_id=['\"]([^'\"]+)['\"]", content)
                dag_id = dag_id_match.group(1) if dag_id_match else file_path.stem

                files.append({
                    "filename": file_path.name,
                    "dag_id": dag_id,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                })
            except Exception as e:
                logger.error(f"Error reading DAG file {file_path}: {e}")
                continue

        return sorted(files, key=lambda x: x["modified_at"], reverse=True)

    def read_dag_file(self, filename: str) -> str | None:
        """
        Read the contents of a DAG file.

        Args:
            filename: Name of the DAG file

        Returns:
            File contents or None if not found
        """
        dags_path = self.get_dags_path()
        file_path = dags_path / filename

        # Security: ensure the file is within the dags directory
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(dags_path.resolve())):
                logger.error(f"Attempted path traversal: {filename}")
                return None
        except Exception:
            return None

        if not file_path.exists() or not file_path.is_file():
            return None

        try:
            return file_path.read_text()
        except Exception as e:
            logger.error(f"Error reading DAG file {filename}: {e}")
            return None

    def write_dag_file(self, filename: str, content: str) -> bool:
        """
        Write or update a DAG file.

        Args:
            filename: Name of the DAG file
            content: Python code content

        Returns:
            True if successful, False otherwise
        """
        dags_path = self.get_dags_path()

        # Ensure filename ends with .py
        if not filename.endswith(".py"):
            filename = f"{filename}.py"

        # Sanitize filename
        filename = re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)

        file_path = dags_path / filename

        # Security: ensure the file is within the dags directory
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(dags_path.resolve())):
                logger.error(f"Attempted path traversal: {filename}")
                return False
        except Exception:
            return False

        try:
            # Ensure dags directory exists
            dags_path.mkdir(parents=True, exist_ok=True)

            # Write the file
            file_path.write_text(content)
            logger.info(f"Written DAG file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing DAG file {filename}: {e}")
            return False

    def delete_dag_file(self, filename: str) -> bool:
        """
        Delete a DAG file.

        Args:
            filename: Name of the DAG file

        Returns:
            True if successful, False otherwise
        """
        dags_path = self.get_dags_path()
        file_path = dags_path / filename

        # Security: ensure the file is within the dags directory
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(dags_path.resolve())):
                logger.error(f"Attempted path traversal: {filename}")
                return False
        except Exception:
            return False

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted DAG file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting DAG file {filename}: {e}")
            return False

    def create_dag_from_template(
        self,
        dag_id: str,
        template: str = "basic",
        description: str = "",
        owner: str = "airflow",
        schedule: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[bool, str]:
        """
        Create a new DAG from a template.

        Args:
            dag_id: Unique DAG identifier
            template: Template name (basic, http_api, data_pipeline)
            description: DAG description
            owner: DAG owner
            schedule: Schedule interval (None, '@daily', '@hourly', etc.)
            tags: List of tags

        Returns:
            Tuple of (success, message/filename)
        """
        if template not in DAG_TEMPLATES:
            return False, f"Unknown template: {template}"

        # Validate dag_id
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', dag_id):
            return False, "dag_id must start with a letter and contain only letters, numbers, and underscores"

        # Check if DAG already exists
        filename = f"{dag_id}.py"
        if (self.get_dags_path() / filename).exists():
            return False, f"DAG file already exists: {filename}"

        # Format schedule for Python
        schedule_str = "None" if schedule is None else f"'{schedule}'"

        # Format tags for Python
        tags_list = tags or []
        tags_str = str(tags_list)

        # Generate DAG content
        content = DAG_TEMPLATES[template].format(
            dag_id=dag_id,
            description=description or f"DAG: {dag_id}",
            owner=owner,
            schedule=schedule_str,
            tags=tags_str,
        )

        if self.write_dag_file(filename, content):
            return True, filename
        else:
            return False, "Failed to write DAG file"

    def get_available_templates(self) -> list[dict[str, str]]:
        """Get list of available DAG templates."""
        return [
            {"id": "basic", "name": "Basic DAG", "description": "Simple DAG with Python operators"},
            {"id": "http_api", "name": "HTTP API DAG", "description": "DAG that calls HTTP APIs"},
            {"id": "data_pipeline", "name": "ETL Pipeline", "description": "Extract, Transform, Load pipeline"},
        ]


# Singleton instance
airflow_client = AirflowClient()
