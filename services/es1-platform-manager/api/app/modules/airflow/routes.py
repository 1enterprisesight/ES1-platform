"""API routes for the Airflow module."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.events import event_bus, EventType
from .client import airflow_client
from .services import airflow_discovery
from .schemas import (
    DAGResponse,
    DAGListResponse,
    DAGRunResponse,
    DAGRunListResponse,
    TriggerDAGRequest,
    TaskInstanceListResponse,
    ConnectionListResponse,
    AirflowHealthResponse,
    DiscoveryResultResponse,
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
    only_active: bool = True,
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
                    schedule_interval=str(d.get("schedule_interval")) if d.get("schedule_interval") else None,
                    tags=[t.get("name", "") for t in d.get("tags", [])],
                    owners=d.get("owners", []),
                    file_token=d.get("file_token"),
                    timetable_description=d.get("timetable_description"),
                    last_parsed_time=d.get("last_parsed_time"),
                    next_dagrun=d.get("next_dagrun"),
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
            schedule_interval=str(d.get("schedule_interval")) if d.get("schedule_interval") else None,
            tags=[t.get("name", "") for t in d.get("tags", [])],
            owners=d.get("owners", []),
            file_token=d.get("file_token"),
            timetable_description=d.get("timetable_description"),
            last_parsed_time=d.get("last_parsed_time"),
            next_dagrun=d.get("next_dagrun"),
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
            EventType.OPERATION_COMPLETED,
            {
                "operation": "trigger_dag",
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

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": f"dag_{action}",
                "dag_id": dag_id,
                "message": f"DAG {dag_id} {action}",
            },
        )

        return {"dag_id": dag_id, "is_paused": result.get("is_paused")}
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
            EventType.OPERATION_COMPLETED,
            {
                "operation": "airflow_discovery",
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
