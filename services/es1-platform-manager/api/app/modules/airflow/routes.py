"""API routes for the Airflow module."""
import io
import zipfile

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.events import event_bus, EventType
from app.modules.gateway.models import DiscoveredResource
from .client import airflow_client
from .services import airflow_discovery
from .connection_templates import get_connection_templates, get_template_categories
from .schemas import (
    DAGResponse,
    DAGListResponse,
    DAGRunResponse,
    DAGRunListResponse,
    TriggerDAGRequest,
    TaskInstanceListResponse,
    ConnectionListResponse,
    ConnectionDetailResponse,
    ConnectionCreateRequest,
    ConnectionUpdateRequest,
    ConnectionDeleteResponse,
    ConnectionTemplateField,
    ConnectionTemplateResponse,
    ConnectionTemplateListResponse,
    AirflowHealthResponse,
    DiscoveryResultResponse,
    DAGFileInfo,
    DAGFileListResponse,
    DAGFileContentResponse,
    DAGFileWriteRequest,
    DAGFileWriteResponse,
    CreateDAGFromTemplateRequest,
    BundleUploadResponse,
    DAGTemplateInfo,
    DAGTemplateListResponse,
)

router = APIRouter(prefix="/airflow", tags=["Airflow"])


@router.get("/health", response_model=AirflowHealthResponse)
async def get_airflow_health():
    """Check Airflow health status."""
    result = await airflow_client.health_check()
    return AirflowHealthResponse(
        status=result.get("status", "unknown"),
        metadatabase=result.get("data", {}).get("metadatabase"),
        scheduler=result.get("data", {}).get("scheduler"),
    )


@router.get("/dags", response_model=DAGListResponse)
async def list_dags(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    only_active: bool = False,
):
    """List all DAGs from Airflow."""
    try:
        result = await airflow_client.list_dags(
            limit=limit,
            offset=offset,
            only_active=only_active,
        )
        return DAGListResponse(
            dags=[
                DAGResponse(
                    dag_id=d["dag_id"],
                    dag_display_name=d.get("dag_display_name"),
                    description=d.get("description"),
                    is_paused=d.get("is_paused", False),
                    is_active=d.get("is_active", True),
                    schedule_interval=str(d.get("timetable_summary") or d.get("schedule_interval")) if (d.get("timetable_summary") or d.get("schedule_interval")) else None,
                    tags=[t.get("name", "") for t in d.get("tags", [])],
                    owners=d.get("owners", []),
                    file_token=d.get("file_token"),
                    timetable_description=d.get("timetable_description"),
                    last_parsed_time=d.get("last_parsed_time"),
                    next_dagrun=d.get("next_dagrun_logical_date") or d.get("next_dagrun"),
                )
                for d in result.get("dags", [])
            ],
            total_entries=result.get("total_entries", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}", response_model=DAGResponse)
async def get_dag(dag_id: str):
    """Get details of a specific DAG."""
    try:
        d = await airflow_client.get_dag(dag_id)
        return DAGResponse(
            dag_id=d["dag_id"],
            dag_display_name=d.get("dag_display_name"),
            description=d.get("description"),
            is_paused=d.get("is_paused", False),
            is_active=d.get("is_active", True),
            schedule_interval=str(d.get("timetable_summary") or d.get("schedule_interval")) if (d.get("timetable_summary") or d.get("schedule_interval")) else None,
            tags=[t.get("name", "") for t in d.get("tags", [])],
            owners=d.get("owners", []),
            file_token=d.get("file_token"),
            timetable_description=d.get("timetable_description"),
            last_parsed_time=d.get("last_parsed_time"),
            next_dagrun=d.get("next_dagrun_logical_date") or d.get("next_dagrun"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dags/{dag_id}/trigger", response_model=DAGRunResponse)
async def trigger_dag(dag_id: str, request: TriggerDAGRequest):
    """Trigger a DAG run."""
    try:
        result = await airflow_client.trigger_dag(
            dag_id=dag_id,
            conf=request.conf,
            logical_date=request.logical_date,
            note=request.note,
        )

        # Emit event
        await event_bus.publish(
            EventType.DAG_TRIGGERED,
            {
                "dag_id": dag_id,
                "dag_run_id": result.get("dag_run_id"),
                "message": f"DAG {dag_id} triggered successfully",
            },
        )

        return DAGRunResponse(
            dag_run_id=result.get("dag_run_id", ""),
            dag_id=result.get("dag_id", dag_id),
            state=result.get("state", "queued"),
            logical_date=result.get("logical_date"),
            start_date=result.get("start_date"),
            end_date=result.get("end_date"),
            execution_date=result.get("execution_date"),
            external_trigger=result.get("external_trigger", True),
            conf=result.get("conf", {}),
            note=result.get("note"),
        )
    except Exception as e:
        await event_bus.publish(
            EventType.OPERATION_FAILED,
            {
                "operation": "trigger_dag",
                "dag_id": dag_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dags/{dag_id}/pause")
async def pause_dag(dag_id: str, is_paused: bool = True):
    """Pause or unpause a DAG."""
    try:
        result = await airflow_client.pause_dag(dag_id, is_paused)
        action = "paused" if is_paused else "unpaused"
        event_type = EventType.DAG_PAUSED if is_paused else EventType.DAG_UNPAUSED

        await event_bus.publish(
            event_type,
            {
                "dag_id": dag_id,
                "message": f"DAG {dag_id} {action}",
            },
        )

        return {"dag_id": dag_id, "is_paused": result.get("is_paused")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dags/{dag_id}/unpause")
async def unpause_dag(dag_id: str):
    """Unpause a DAG. Convenience endpoint used by the UI."""
    return await pause_dag(dag_id, is_paused=False)


@router.get("/dag-runs", response_model=DAGRunListResponse)
async def list_all_dag_runs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: str | None = None,
):
    """List DAG runs across all DAGs."""
    try:
        result = await airflow_client.get_all_dag_runs(
            limit=limit,
            offset=offset,
            state=state,
        )
        return DAGRunListResponse(
            dag_runs=[
                DAGRunResponse(
                    dag_run_id=r.get("dag_run_id", ""),
                    dag_id=r.get("dag_id", ""),
                    state=r.get("state", ""),
                    logical_date=r.get("logical_date"),
                    start_date=r.get("start_date"),
                    end_date=r.get("end_date"),
                    execution_date=r.get("execution_date"),
                    external_trigger=r.get("external_trigger", False),
                    conf=r.get("conf", {}),
                    note=r.get("note"),
                )
                for r in result.get("dag_runs", [])
            ],
            total_entries=result.get("total_entries", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}/runs", response_model=DAGRunListResponse)
async def list_dag_runs(
    dag_id: str,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: str | None = None,
):
    """List DAG runs for a specific DAG."""
    try:
        result = await airflow_client.get_dag_runs(
            dag_id=dag_id,
            limit=limit,
            offset=offset,
            state=state,
        )
        return DAGRunListResponse(
            dag_runs=[
                DAGRunResponse(
                    dag_run_id=r.get("dag_run_id", ""),
                    dag_id=r.get("dag_id", dag_id),
                    state=r.get("state", ""),
                    logical_date=r.get("logical_date"),
                    start_date=r.get("start_date"),
                    end_date=r.get("end_date"),
                    execution_date=r.get("execution_date"),
                    external_trigger=r.get("external_trigger", False),
                    conf=r.get("conf", {}),
                    note=r.get("note"),
                )
                for r in result.get("dag_runs", [])
            ],
            total_entries=result.get("total_entries", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}/runs/{dag_run_id}", response_model=DAGRunResponse)
async def get_dag_run(dag_id: str, dag_run_id: str):
    """Get details of a specific DAG run."""
    try:
        r = await airflow_client.get_dag_run(dag_id, dag_run_id)
        return DAGRunResponse(
            dag_run_id=r.get("dag_run_id", dag_run_id),
            dag_id=r.get("dag_id", dag_id),
            state=r.get("state", ""),
            logical_date=r.get("logical_date"),
            start_date=r.get("start_date"),
            end_date=r.get("end_date"),
            execution_date=r.get("execution_date"),
            external_trigger=r.get("external_trigger", False),
            conf=r.get("conf", {}),
            note=r.get("note"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}/runs/{dag_run_id}/tasks", response_model=TaskInstanceListResponse)
async def get_task_instances(dag_id: str, dag_run_id: str):
    """Get task instances for a DAG run."""
    try:
        result = await airflow_client.get_task_instances(dag_id, dag_run_id)
        from .schemas import TaskInstanceResponse
        return TaskInstanceListResponse(
            task_instances=[
                TaskInstanceResponse(
                    task_id=t.get("task_id", ""),
                    dag_id=t.get("dag_id", dag_id),
                    dag_run_id=t.get("dag_run_id", dag_run_id),
                    state=t.get("state"),
                    start_date=t.get("start_date"),
                    end_date=t.get("end_date"),
                    duration=t.get("duration"),
                    try_number=t.get("try_number", 1),
                    operator=t.get("operator"),
                )
                for t in result.get("task_instances", [])
            ],
            total_entries=len(result.get("task_instances", [])),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections", response_model=ConnectionListResponse)
async def list_connections(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List Airflow connections."""
    try:
        result = await airflow_client.get_connections(limit=limit, offset=offset)
        from .schemas import ConnectionResponse
        return ConnectionListResponse(
            connections=[
                ConnectionResponse(
                    connection_id=c.get("connection_id", ""),
                    conn_type=c.get("conn_type"),
                    description=c.get("description"),
                    host=c.get("host"),
                    port=c.get("port"),
                    schema_name=c.get("schema"),
                )
                for c in result.get("connections", [])
            ],
            total_entries=result.get("total_entries", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}", response_model=ConnectionDetailResponse)
async def get_connection(connection_id: str):
    """Get details of a specific connection."""
    try:
        c = await airflow_client.get_connection(connection_id)
        return ConnectionDetailResponse(
            connection_id=c.get("connection_id", connection_id),
            conn_type=c.get("conn_type"),
            description=c.get("description"),
            host=c.get("host"),
            port=c.get("port"),
            schema_name=c.get("schema"),
            login=c.get("login"),
            extra=c.get("extra"),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connections", response_model=ConnectionDetailResponse)
async def create_connection(request: ConnectionCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new Airflow connection."""
    try:
        # Map schema_name -> schema for Airflow API
        payload = {
            "connection_id": request.connection_id,
            "conn_type": request.conn_type,
        }
        if request.description is not None:
            payload["description"] = request.description
        if request.host is not None:
            payload["host"] = request.host
        if request.port is not None:
            payload["port"] = request.port
        if request.schema_name is not None:
            payload["schema"] = request.schema_name
        if request.login is not None:
            payload["login"] = request.login
        if request.password is not None:
            payload["password"] = request.password
        if request.extra is not None:
            payload["extra"] = request.extra

        c = await airflow_client.create_connection(payload)

        # Trigger gateway sync for connections
        await airflow_discovery.discover_connections(db)

        return ConnectionDetailResponse(
            connection_id=c.get("connection_id", request.connection_id),
            conn_type=c.get("conn_type"),
            description=c.get("description"),
            host=c.get("host"),
            port=c.get("port"),
            schema_name=c.get("schema"),
            login=c.get("login"),
            extra=c.get("extra"),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(status_code=409, detail=f"Connection already exists: {request.connection_id}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/connections/{connection_id}", response_model=ConnectionDetailResponse)
async def update_connection(connection_id: str, request: ConnectionUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update an existing Airflow connection."""
    try:
        # Build payload with only provided fields, mapping schema_name -> schema
        payload: dict = {}
        if request.conn_type is not None:
            payload["conn_type"] = request.conn_type
        if request.description is not None:
            payload["description"] = request.description
        if request.host is not None:
            payload["host"] = request.host
        if request.port is not None:
            payload["port"] = request.port
        if request.schema_name is not None:
            payload["schema"] = request.schema_name
        if request.login is not None:
            payload["login"] = request.login
        if request.password is not None:
            payload["password"] = request.password
        if request.extra is not None:
            payload["extra"] = request.extra

        c = await airflow_client.update_connection(connection_id, payload)

        # Trigger gateway sync
        await airflow_discovery.discover_connections(db)

        return ConnectionDetailResponse(
            connection_id=c.get("connection_id", connection_id),
            conn_type=c.get("conn_type"),
            description=c.get("description"),
            host=c.get("host"),
            port=c.get("port"),
            schema_name=c.get("schema"),
            login=c.get("login"),
            extra=c.get("extra"),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connection not found: {connection_id}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connections/{connection_id}", response_model=ConnectionDeleteResponse)
async def delete_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an Airflow connection and mark gateway resource as deleted."""
    try:
        success = await airflow_client.delete_connection(connection_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete connection: {connection_id}")

        # Mark corresponding gateway resource as deleted
        query = select(DiscoveredResource).where(
            DiscoveredResource.source == "airflow",
            DiscoveredResource.source_id == connection_id,
            DiscoveredResource.type == "connection",
            DiscoveredResource.status != "deleted",
        )
        result = await db.execute(query)
        resource = result.scalar_one_or_none()
        if resource:
            resource.status = "deleted"
            await db.commit()

        return ConnectionDeleteResponse(
            success=True,
            message=f"Connection {connection_id} deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connection-templates", response_model=ConnectionTemplateListResponse)
async def list_connection_templates():
    """List available connection templates."""
    templates = get_connection_templates()
    categories = get_template_categories()
    return ConnectionTemplateListResponse(
        templates=[
            ConnectionTemplateResponse(
                conn_type=t["conn_type"],
                display_name=t["display_name"],
                description=t["description"],
                category=t["category"],
                default_port=t.get("default_port"),
                fields=[ConnectionTemplateField(**f) for f in t["fields"]],
                extra_schema=t.get("extra_schema", {}),
            )
            for t in templates
        ],
        categories=categories,
    )


@router.post("/discover", response_model=DiscoveryResultResponse)
async def discover_resources(db: AsyncSession = Depends(get_db)):
    """Discover all resources from Airflow and sync to database."""
    try:
        await event_bus.publish(
            EventType.OPERATION_STARTED,
            {
                "operation": "airflow_discovery",
                "message": "Starting Airflow resource discovery...",
            },
        )

        result = await airflow_discovery.discover_all(db)

        dags_count = len(result.get("dags", []))
        connections_count = len(result.get("connections", []))

        await event_bus.publish(
            EventType.DAG_DISCOVERED,
            {
                "dags_discovered": dags_count,
                "connections_discovered": connections_count,
                "message": f"Discovered {dags_count} DAGs and {connections_count} connections",
            },
        )

        return DiscoveryResultResponse(
            dags_discovered=dags_count,
            connections_discovered=connections_count,
            message=f"Successfully discovered {dags_count} DAGs and {connections_count} connections",
        )
    except Exception as e:
        await event_bus.publish(
            EventType.OPERATION_FAILED,
            {
                "operation": "airflow_discovery",
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DAG File Management Routes
# =============================================================================

@router.get("/dag-files", response_model=DAGFileListResponse)
async def list_dag_files(db: AsyncSession = Depends(get_db)):
    """List all DAG files."""
    files = await airflow_client.list_dag_files(db)
    return DAGFileListResponse(
        files=[DAGFileInfo(**f) for f in files],
        total=len(files),
        dags_path="db://dag_files",
    )


@router.get("/dag-files/{filename:path}", response_model=DAGFileContentResponse)
async def get_dag_file(filename: str, db: AsyncSession = Depends(get_db)):
    """Get the content of a DAG file."""
    content = await airflow_client.read_dag_file(filename, db)
    if content is None:
        raise HTTPException(status_code=404, detail=f"DAG file not found: {filename}")

    return DAGFileContentResponse(
        filename=filename,
        content=content,
        size=len(content),
    )


@router.put("/dag-files", response_model=DAGFileWriteResponse)
async def write_dag_file(request: DAGFileWriteRequest, db: AsyncSession = Depends(get_db)):
    """Create or update a DAG file."""
    success = await airflow_client.write_dag_file(request.filename, request.content, db)

    if success:
        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "dag_file_saved",
                "filename": request.filename,
                "message": f"DAG file {request.filename} saved",
            },
        )
        return DAGFileWriteResponse(
            success=True,
            filename=request.filename,
            message=f"DAG file {request.filename} saved successfully",
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to write DAG file")


@router.delete("/dag-files/{filename:path}")
async def delete_dag_file(filename: str, db: AsyncSession = Depends(get_db)):
    """Delete a DAG file, deregister from Airflow, and mark gateway resource as deleted."""
    # Read dag_id from file before deleting
    import re
    content = await airflow_client.read_dag_file(filename, db)
    dag_id = None
    if content:
        match = re.search(r"dag_id=['\"]([^'\"]+)['\"]", content)
        if not match:
            match = re.search(r"DAG\(\s*['\"]([^'\"]+)['\"]", content)
        if match:
            dag_id = match.group(1)

    success = await airflow_client.delete_dag_file(filename, db)
    if not success:
        raise HTTPException(status_code=404, detail=f"DAG file not found: {filename}")

    # Also delete from Airflow's metadata to keep things in sync
    if dag_id:
        await airflow_client.delete_dag(dag_id)

        # Mark corresponding gateway resource as deleted
        query = select(DiscoveredResource).where(
            DiscoveredResource.source == "airflow",
            DiscoveredResource.source_id == dag_id,
            DiscoveredResource.type == "workflow",
            DiscoveredResource.status != "deleted",
        )
        result = await db.execute(query)
        resource = result.scalar_one_or_none()
        if resource:
            resource.status = "deleted"
            await db.commit()

    await event_bus.publish(
        EventType.OPERATION_COMPLETED,
        {
            "operation": "dag_file_deleted",
            "filename": filename,
            "dag_id": dag_id,
            "message": f"DAG file {filename} deleted",
        },
    )

    return {"success": True, "message": f"DAG file {filename} deleted"}


@router.post("/dags/cleanup")
async def cleanup_stale_dags(db: AsyncSession = Depends(get_db)):
    """Remove DAGs from Airflow that no longer have files in the database, and mark gateway resources as deleted."""
    try:
        # Get all Airflow DAGs
        result = await airflow_client.list_dags(limit=1000, only_active=False)
        airflow_dags = {d["dag_id"] for d in result.get("dags", [])}

        # Get all DAG file dag_ids from database
        files = await airflow_client.list_dag_files(db)
        file_dag_ids = {f["dag_id"] for f in files}

        # Find stale DAGs (in Airflow but no file in database)
        stale = airflow_dags - file_dag_ids
        removed = []
        for dag_id in stale:
            if await airflow_client.delete_dag(dag_id):
                removed.append(dag_id)
                # Mark gateway resource as deleted
                query = select(DiscoveredResource).where(
                    DiscoveredResource.source == "airflow",
                    DiscoveredResource.source_id == dag_id,
                    DiscoveredResource.type == "workflow",
                    DiscoveredResource.status != "deleted",
                )
                res = await db.execute(query)
                resource = res.scalar_one_or_none()
                if resource:
                    resource.status = "deleted"

        await db.commit()

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "dag_cleanup",
                "removed": removed,
                "message": f"Removed {len(removed)} stale DAGs",
            },
        )

        return {
            "success": True,
            "removed": removed,
            "message": f"Removed {len(removed)} stale DAGs: {', '.join(removed) if removed else 'none'}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dag-files/upload-bundle", response_model=BundleUploadResponse)
async def upload_dag_bundle(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a zip bundle containing DAG files and helper modules.

    The zip should contain a directory with Python files. All .py files
    are extracted and stored in the database with their relative paths
    preserved (e.g., my_bundle/dag.py, my_bundle/utils/helpers.py).
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Bundle too large (max 10MB)")

    try:
        zf = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")

    # Extract Python files
    py_files = [
        name for name in zf.namelist()
        if name.endswith(".py") and not name.startswith("__MACOSX")
    ]

    if not py_files:
        raise HTTPException(status_code=400, detail="No .py files found in zip")

    # Find common prefix (bundle directory name)
    # e.g., if zip contains my_bundle/dag.py, my_bundle/utils.py → prefix is "my_bundle/"
    parts = [name.split("/") for name in py_files]
    if len(parts[0]) > 1 and all(p[0] == parts[0][0] for p in parts):
        bundle_name = parts[0][0]
    else:
        # No common directory — use the zip filename as bundle name
        bundle_name = file.filename.replace(".zip", "")

    uploaded = []
    for py_path in py_files:
        content = zf.read(py_path).decode("utf-8")
        # Use the path as-is if it has a directory prefix, otherwise add bundle_name
        if "/" in py_path:
            filename = py_path
        else:
            filename = f"{bundle_name}/{py_path}"

        success = await airflow_client.write_dag_file(filename, content, db)
        if success:
            uploaded.append(filename)

    if not uploaded:
        raise HTTPException(status_code=500, detail="Failed to store any files from bundle")

    await event_bus.publish(
        EventType.OPERATION_COMPLETED,
        {
            "operation": "bundle_uploaded",
            "bundle_name": bundle_name,
            "files": uploaded,
            "message": f"Bundle {bundle_name} uploaded with {len(uploaded)} files",
        },
    )

    return BundleUploadResponse(
        success=True,
        bundle_name=bundle_name,
        files_uploaded=uploaded,
        message=f"Uploaded {len(uploaded)} files from bundle '{bundle_name}'",
    )


@router.get("/dags/{dag_id}/source")
async def get_dag_source(dag_id: str, db: AsyncSession = Depends(get_db)):
    """Get the source code for a DAG.

    First checks the dag_files database, then falls back to Airflow's
    dagSources API. This allows viewing source for any DAG, whether it
    was created via the platform or loaded from the dags-folder.
    """
    # Try database first (platform-managed DAGs)
    from app.modules.airflow.models import DagFile
    result = await db.execute(
        select(DagFile).where(DagFile.dag_id == dag_id)
    )
    dag_file = result.scalar_one_or_none()
    if dag_file:
        return {
            "dag_id": dag_id,
            "source": dag_file.content,
            "filename": dag_file.filename,
            "origin": "platform",
        }

    # Fall back to Airflow dagSources API (v2 uses dag_id directly)
    try:
        source = await airflow_client.get_dag_source(dag_id)
        if source is None:
            raise HTTPException(status_code=404, detail=f"Could not fetch source for DAG: {dag_id}")

        return {
            "dag_id": dag_id,
            "source": source,
            "filename": None,
            "origin": "airflow",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dags/{dag_id}/import")
async def import_dag_to_platform(dag_id: str, db: AsyncSession = Depends(get_db)):
    """Import a DAG from Airflow into the platform database.

    Fetches source from Airflow's dagSources API and stores it in the
    dag_files table so it becomes editable in the DAG Editor.
    """
    # Check if already in database
    from app.modules.airflow.models import DagFile
    result = await db.execute(
        select(DagFile).where(DagFile.dag_id == dag_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"DAG {dag_id} is already managed by the platform")

    # Fetch from Airflow (v2 API uses dag_id directly)
    try:
        source = await airflow_client.get_dag_source(dag_id)
        if source is None:
            raise HTTPException(status_code=404, detail=f"Could not fetch source for DAG: {dag_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Store in database
    filename = f"{dag_id}.py"
    success = await airflow_client.write_dag_file(filename, source, db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to import DAG")

    await event_bus.publish(
        EventType.OPERATION_COMPLETED,
        {
            "operation": "dag_imported",
            "dag_id": dag_id,
            "filename": filename,
            "message": f"DAG {dag_id} imported to platform",
        },
    )

    return {
        "success": True,
        "dag_id": dag_id,
        "filename": filename,
        "message": f"DAG {dag_id} imported to platform editor",
    }


@router.get("/dag-templates", response_model=DAGTemplateListResponse)
async def list_dag_templates():
    """List available DAG templates."""
    templates = airflow_client.get_available_templates()
    return DAGTemplateListResponse(
        templates=[DAGTemplateInfo(**t) for t in templates]
    )


@router.post("/dag-files/from-template", response_model=DAGFileWriteResponse)
async def create_dag_from_template(request: CreateDAGFromTemplateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new DAG file from a template."""
    success, result = await airflow_client.create_dag_from_template(
        dag_id=request.dag_id,
        db=db,
        template=request.template,
        description=request.description,
        owner=request.owner,
        schedule=request.schedule,
        tags=request.tags,
    )

    if success:
        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "dag_created",
                "dag_id": request.dag_id,
                "filename": result,
                "message": f"DAG {request.dag_id} created from template {request.template}",
            },
        )
        return DAGFileWriteResponse(
            success=True,
            filename=result,
            message=f"DAG {request.dag_id} created successfully",
        )
    else:
        raise HTTPException(status_code=400, detail=result)
