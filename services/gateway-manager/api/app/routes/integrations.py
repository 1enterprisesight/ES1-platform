"""Integration routes for external systems."""
import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.core.runtime import RUNTIME_MODE, RuntimeMode
from app.models import DiscoveredResource, EventLog

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Global token cache (per pod, in-memory)
_token_cache: Dict[str, Dict[str, Any]] = {}


async def get_airflow_credentials() -> Dict[str, str]:
    """
    Get Airflow credentials from appropriate source based on runtime mode.

    - Docker mode: Read from environment variables
    - Kubernetes mode: Read from Kubernetes Secret
    """
    if RUNTIME_MODE == RuntimeMode.DOCKER:
        # Docker mode: use environment variables
        return {
            "username": settings.AIRFLOW_USERNAME,
            "password": settings.AIRFLOW_PASSWORD,
            "url": settings.AIRFLOW_API_URL.rstrip("/api/v1")  # Base URL without API path
        }

    # Kubernetes mode: read from secret
    try:
        from kubernetes import client, config

        config.load_incluster_config()
        v1 = client.CoreV1Api()
        secret = v1.read_namespaced_secret(
            name=settings.AIRFLOW_CREDENTIALS_SECRET,
            namespace=settings.AIRFLOW_CREDENTIALS_NAMESPACE
        )

        # Decode base64-encoded values
        username = base64.b64decode(secret.data["username"]).decode("utf-8")
        password = base64.b64decode(secret.data["password"]).decode("utf-8")
        url = base64.b64decode(secret.data["url"]).decode("utf-8")

        return {
            "username": username,
            "password": password,
            "url": url
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read Airflow credentials: {str(e)}"
        )


async def get_airflow_jwt_token() -> tuple[str, str]:
    """
    Get JWT token for Airflow API authentication.
    Uses cached token if valid, otherwise fetches new token.

    Returns:
        Tuple of (token, url)
    """
    # Check cache
    cached = _token_cache.get("airflow")
    if cached and cached["expires_at"] > datetime.utcnow().timestamp():
        return cached["token"], cached["url"]

    # Cache miss or expired - get new token
    creds = await get_airflow_credentials()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{creds['url']}/auth/token",
                json={
                    "username": creds["username"],
                    "password": creds["password"]
                }
            )
            response.raise_for_status()
            data = response.json()
            token = data["access_token"]
    except httpx.HTTPStatusError as e:
        # If JWT auth fails, try basic auth (some Airflow configs use basic auth)
        # Return None token to indicate basic auth should be used
        return None, creds["url"]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to obtain Airflow JWT token: {str(e)}"
        )

    # Cache token (23 hours = 24h - 1h buffer)
    expires_at = datetime.utcnow() + timedelta(hours=23)
    _token_cache["airflow"] = {
        "token": token,
        "url": creds["url"],
        "expires_at": expires_at.timestamp()
    }

    return token, creds["url"]


async def get_auth_headers() -> tuple[Dict[str, str], str]:
    """
    Get authentication headers for Airflow API.

    Returns:
        Tuple of (headers dict, base url)
    """
    token, url = await get_airflow_jwt_token()

    if token:
        # JWT authentication
        return {"Authorization": f"Bearer {token}"}, url
    else:
        # Basic authentication fallback
        creds = await get_airflow_credentials()
        import base64 as b64
        auth_string = b64.b64encode(
            f"{creds['username']}:{creds['password']}".encode()
        ).decode()
        return {"Authorization": f"Basic {auth_string}"}, url


async def fetch_airflow_dags(headers: Dict[str, str], url: str) -> list[Dict[str, Any]]:
    """Fetch all DAGs from Airflow with pagination."""
    all_dags = []
    limit = 100
    offset = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(
                f"{url}/api/v1/dags",
                params={"limit": limit, "offset": offset},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            dags = data.get("dags", [])
            if not dags:
                break

            all_dags.extend(dags)

            # Check if there are more results
            total_entries = data.get("total_entries", 0)
            if offset + limit >= total_entries:
                break

            offset += limit

    return all_dags


async def fetch_airflow_connections(headers: Dict[str, str], url: str) -> list[Dict[str, Any]]:
    """Fetch all Connections from Airflow with pagination."""
    all_connections = []
    limit = 100
    offset = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(
                f"{url}/api/v1/connections",
                params={"limit": limit, "offset": offset},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            connections = data.get("connections", [])
            if not connections:
                break

            all_connections.extend(connections)

            # Check if there are more results
            total_entries = data.get("total_entries", 0)
            if offset + limit >= total_entries:
                break

            offset += limit

    return all_connections


@router.post("/airflow/sync")
async def sync_airflow_resources(db: AsyncSession = Depends(get_db)):
    """
    Sync resources from Airflow to local database.

    This endpoint:
    1. Gets authentication headers (JWT or Basic auth)
    2. Fetches all DAGs and Connections from Airflow API v2 (with pagination)
    3. UPSERTs resources into discovered_resources table
    4. Marks resources no longer in Airflow as inactive
    5. Returns sync summary
    """
    try:
        # Get auth headers
        headers, url = await get_auth_headers()

        # Fetch DAGs and Connections
        dags = await fetch_airflow_dags(headers, url)
        connections = await fetch_airflow_connections(headers, url)

        # Track synced resource names
        synced_names = set()
        added_count = 0
        updated_count = 0

        # Process DAGs
        for dag in dags:
            dag_id = dag.get("dag_id")
            if not dag_id:
                continue

            synced_names.add(dag_id)

            # Check if resource exists
            result = await db.execute(
                select(DiscoveredResource).where(
                    DiscoveredResource.source_id == dag_id,
                    DiscoveredResource.source == "airflow"
                )
            )
            existing = result.scalar_one_or_none()

            # Prepare metadata
            metadata = {
                "airflow_dag_id": dag_id,
                "dag_id": dag_id,  # Also store as dag_id for config generator
                "description": dag.get("description", ""),
                "is_paused": dag.get("is_paused", False),
                "schedule_interval": dag.get("schedule_interval"),
                "owners": dag.get("owners", []),
                "fileloc": dag.get("fileloc"),
                "tags": dag.get("tags", [])
            }

            if existing:
                # Update existing resource
                existing.resource_metadata = metadata
                existing.status = "active"
                existing.discovered_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new resource
                new_resource = DiscoveredResource(
                    source_id=dag_id,
                    type="workflow",
                    source="airflow",
                    status="active",
                    resource_metadata=metadata
                )
                db.add(new_resource)
                await db.flush()  # Get ID for event logging

                # Log resource discovered event
                event = EventLog(
                    event_type="resource_discovered",
                    entity_type="resource",
                    entity_id=new_resource.id,
                    user_id="system",
                    event_metadata={
                        "resource_type": "workflow",
                        "resource_name": dag_id,
                        "source": "airflow"
                    }
                )
                db.add(event)
                added_count += 1

        # Process Connections
        for conn in connections:
            conn_id = conn.get("connection_id")
            if not conn_id:
                continue

            synced_names.add(conn_id)

            # Check if resource exists
            result = await db.execute(
                select(DiscoveredResource).where(
                    DiscoveredResource.source_id == conn_id,
                    DiscoveredResource.source == "airflow"
                )
            )
            existing = result.scalar_one_or_none()

            # Prepare metadata (DO NOT store password)
            metadata = {
                "airflow_connection_id": conn_id,
                "conn_id": conn_id,  # Also store as conn_id for config generator
                "description": conn.get("description", ""),
                "conn_type": conn.get("conn_type"),
                "host": conn.get("host"),
                "port": conn.get("port"),
                "schema": conn.get("schema"),
                "login": conn.get("login"),
                "extra": conn.get("extra")  # May contain additional config
            }

            if existing:
                # Update existing resource
                existing.resource_metadata = metadata
                existing.status = "active"
                existing.discovered_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new resource
                new_resource = DiscoveredResource(
                    source_id=conn_id,
                    type="connection",
                    source="airflow",
                    status="active",
                    resource_metadata=metadata
                )
                db.add(new_resource)
                await db.flush()  # Get ID for event logging

                # Log resource discovered event
                event = EventLog(
                    event_type="resource_discovered",
                    entity_type="resource",
                    entity_id=new_resource.id,
                    user_id="system",
                    event_metadata={
                        "resource_type": "connection",
                        "resource_name": conn_id,
                        "source": "airflow"
                    }
                )
                db.add(event)
                added_count += 1

        # Mark resources no longer in Airflow as inactive
        result = await db.execute(
            select(DiscoveredResource).where(
                DiscoveredResource.source == "airflow",
                DiscoveredResource.status == "active"
            )
        )
        all_airflow_resources = result.scalars().all()

        inactive_count = 0
        for resource in all_airflow_resources:
            if resource.source_id not in synced_names:
                resource.status = "inactive"
                inactive_count += 1

        # Commit transaction
        await db.commit()

        return {
            "success": True,
            "runtime_mode": RUNTIME_MODE.value,
            "summary": {
                "dags_synced": len(dags),
                "connections_synced": len(connections),
                "resources_added": added_count,
                "resources_updated": updated_count,
                "resources_marked_inactive": inactive_count,
                "total_synced": len(synced_names)
            }
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"Airflow API error: {e.response.text if e.response else str(e)}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/airflow/status")
async def get_airflow_status():
    """Get Airflow integration status and configuration."""
    return {
        "enabled": True,
        "runtime_mode": RUNTIME_MODE.value,
        "api_url": settings.AIRFLOW_API_URL,
        "backend_host": settings.AIRFLOW_BACKEND_HOST,
        "credentials_source": "environment" if RUNTIME_MODE == RuntimeMode.DOCKER else "kubernetes_secret",
    }


@router.get("/langflow/status")
async def get_langflow_status():
    """Get Langflow integration status and configuration."""
    # Check if Langflow is reachable
    is_healthy = False
    if settings.LANGFLOW_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.LANGFLOW_URL}/health")
                is_healthy = response.status_code == 200
        except Exception:
            pass

    return {
        "enabled": settings.LANGFLOW_ENABLED,
        "url": settings.LANGFLOW_URL,
        "api_url": settings.LANGFLOW_API_URL,
        "healthy": is_healthy,
    }


@router.post("/langflow/sync")
async def sync_langflow_resources(db: AsyncSession = Depends(get_db)):
    """
    Sync flows from Langflow to local database.

    This endpoint:
    1. Fetches all flows from Langflow API
    2. UPSERTs flows into discovered_resources table
    3. Marks flows no longer in Langflow as inactive
    4. Returns sync summary
    """
    if not settings.LANGFLOW_ENABLED:
        raise HTTPException(status_code=400, detail="Langflow integration is disabled")

    try:
        from app.services.langflow_client import LangflowClient

        client = LangflowClient()

        # Check health first
        if not await client.health_check():
            raise HTTPException(status_code=503, detail="Langflow is not reachable")

        # Fetch all flows
        flows = await client.list_flows()

        # Track synced flow IDs
        synced_ids = set()
        added_count = 0
        updated_count = 0

        for flow in flows:
            flow_id = flow.get("id")
            if not flow_id:
                continue

            synced_ids.add(flow_id)

            # Check if resource exists
            result = await db.execute(
                select(DiscoveredResource).where(
                    DiscoveredResource.source_id == flow_id,
                    DiscoveredResource.source == "langflow"
                )
            )
            existing = result.scalar_one_or_none()

            # Prepare metadata
            metadata = {
                "flow_id": flow_id,
                "name": flow.get("name", ""),
                "description": flow.get("description", ""),
                "endpoint_name": flow.get("endpoint_name"),
                "is_component": flow.get("is_component", False),
                "folder_id": flow.get("folder_id"),
                "updated_at": flow.get("updated_at"),
            }

            if existing:
                # Update existing resource
                existing.resource_metadata = metadata
                existing.status = "active"
                existing.discovered_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new resource
                new_resource = DiscoveredResource(
                    source_id=flow_id,
                    type="flow",
                    source="langflow",
                    status="active",
                    resource_metadata=metadata
                )
                db.add(new_resource)
                await db.flush()

                # Log resource discovered event
                event = EventLog(
                    event_type="resource_discovered",
                    entity_type="resource",
                    entity_id=new_resource.id,
                    user_id="system",
                    event_metadata={
                        "resource_type": "flow",
                        "resource_name": flow.get("name", flow_id),
                        "source": "langflow"
                    }
                )
                db.add(event)
                added_count += 1

        # Mark flows no longer in Langflow as inactive
        result = await db.execute(
            select(DiscoveredResource).where(
                DiscoveredResource.source == "langflow",
                DiscoveredResource.status == "active"
            )
        )
        all_langflow_resources = result.scalars().all()

        inactive_count = 0
        for resource in all_langflow_resources:
            if resource.source_id not in synced_ids:
                resource.status = "inactive"
                inactive_count += 1

        # Commit transaction
        await db.commit()

        return {
            "success": True,
            "summary": {
                "flows_synced": len(flows),
                "resources_added": added_count,
                "resources_updated": updated_count,
                "resources_marked_inactive": inactive_count,
            }
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"Langflow API error: {e.response.text if e.response else str(e)}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/langfuse/status")
async def get_langfuse_status():
    """Get Langfuse integration status and configuration."""
    # Check if Langfuse is reachable
    is_healthy = False
    if settings.LANGFUSE_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.LANGFUSE_URL}/api/public/health")
                is_healthy = response.status_code == 200
        except Exception:
            pass

    return {
        "enabled": settings.LANGFUSE_ENABLED,
        "url": settings.LANGFUSE_URL,
        "api_url": settings.LANGFUSE_API_URL,
        "healthy": is_healthy,
    }
