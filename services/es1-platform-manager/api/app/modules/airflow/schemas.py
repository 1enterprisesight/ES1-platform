"""Pydantic schemas for the Airflow module."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class DAGBase(BaseModel):
    """Base DAG schema."""
    dag_id: str
    dag_display_name: str | None = None
    description: str | None = None
    is_paused: bool = False
    is_active: bool = True
    schedule_interval: str | None = None
    tags: list[str] = []
    owners: list[str] = []


class DAGResponse(DAGBase):
    """Schema for DAG response."""
    file_token: str | None = None
    timetable_description: str | None = None
    last_parsed_time: str | None = None
    next_dagrun: str | None = None

    class Config:
        from_attributes = True


class DAGListResponse(BaseModel):
    """Schema for DAG list response."""
    dags: list[DAGResponse]
    total_entries: int


class DAGRunBase(BaseModel):
    """Base DAG run schema."""
    dag_run_id: str
    dag_id: str
    state: str
    logical_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class DAGRunResponse(DAGRunBase):
    """Schema for DAG run response."""
    execution_date: str | None = None
    external_trigger: bool = False
    conf: dict[str, Any] = {}
    note: str | None = None

    class Config:
        from_attributes = True


class DAGRunListResponse(BaseModel):
    """Schema for DAG run list response."""
    dag_runs: list[DAGRunResponse]
    total_entries: int


class TriggerDAGRequest(BaseModel):
    """Schema for triggering a DAG."""
    conf: dict[str, Any] | None = None
    logical_date: str | None = None
    note: str | None = None


class TaskInstanceResponse(BaseModel):
    """Schema for task instance response."""
    task_id: str
    dag_id: str
    dag_run_id: str
    state: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration: float | None = None
    try_number: int = 1
    operator: str | None = None


class TaskInstanceListResponse(BaseModel):
    """Schema for task instance list response."""
    task_instances: list[TaskInstanceResponse]
    total_entries: int


class ConnectionResponse(BaseModel):
    """Schema for connection response."""
    connection_id: str
    conn_type: str | None = None
    description: str | None = None
    host: str | None = None
    port: int | None = None
    schema_name: str | None = None


class ConnectionListResponse(BaseModel):
    """Schema for connection list response."""
    connections: list[ConnectionResponse]
    total_entries: int


class AirflowHealthResponse(BaseModel):
    """Schema for Airflow health response."""
    status: str
    metadatabase: dict[str, Any] | None = None
    scheduler: dict[str, Any] | None = None


class DiscoveryResultResponse(BaseModel):
    """Schema for discovery result."""
    dags_discovered: int
    connections_discovered: int
    message: str
