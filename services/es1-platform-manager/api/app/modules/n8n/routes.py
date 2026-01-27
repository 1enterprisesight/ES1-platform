"""API routes for n8n workflow automation."""
from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from .client import n8n_client, N8NAPIKeyMissingError
from .schemas import (
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowDetailResponse,
    ExecuteWorkflowRequest,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionDetailResponse,
    CredentialResponse,
    CredentialListResponse,
    N8NHealthResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/n8n", tags=["n8n"])


@router.get("/health", response_model=N8NHealthResponse)
async def check_n8n_health():
    """Check n8n service health."""
    result = await n8n_client.health_check()
    return N8NHealthResponse(
        status=result.get("status", "unknown"),
        message=result.get("data", {}).get("message") if result.get("data") else result.get("message"),
        error=result.get("error"),
        setup_url=result.get("setup_url"),
    )


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(active: bool | None = None):
    """List all n8n workflows."""
    try:
        result = await n8n_client.list_workflows(active=active)
        workflows = result.get("data", [])

        return WorkflowListResponse(
            workflows=[
                WorkflowResponse(
                    id=str(w.get("id", "")),
                    name=w.get("name", ""),
                    active=w.get("active", False),
                    created_at=w.get("createdAt"),
                    updated_at=w.get("updatedAt"),
                    tags=[t.get("name", "") for t in w.get("tags", [])],
                    nodes_count=len(w.get("nodes", [])),
                )
                for w in workflows
            ],
            total=len(workflows),
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow(workflow_id: str):
    """Get details of a specific workflow."""
    try:
        w = await n8n_client.get_workflow(workflow_id)

        return WorkflowDetailResponse(
            id=str(w.get("id", "")),
            name=w.get("name", ""),
            active=w.get("active", False),
            created_at=w.get("createdAt"),
            updated_at=w.get("updatedAt"),
            tags=[t.get("name", "") for t in w.get("tags", [])],
            nodes_count=len(w.get("nodes", [])),
            nodes=w.get("nodes", []),
            connections=w.get("connections", {}),
            settings=w.get("settings", {}),
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(workflow_id: str, request: ExecuteWorkflowRequest | None = None):
    """Execute a workflow."""
    try:
        data = request.data if request else None
        result = await n8n_client.execute_workflow(workflow_id, data=data)

        execution = result.get("data", {})
        return ExecutionResponse(
            id=str(execution.get("id", "")),
            workflow_id=workflow_id,
            workflow_name=execution.get("workflowData", {}).get("name"),
            status=execution.get("status", "running"),
            started_at=execution.get("startedAt"),
            finished_at=execution.get("stoppedAt"),
            mode=execution.get("mode"),
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/activate", response_model=WorkflowResponse)
async def activate_workflow(workflow_id: str):
    """Activate a workflow."""
    try:
        w = await n8n_client.activate_workflow(workflow_id, active=True)

        return WorkflowResponse(
            id=str(w.get("id", "")),
            name=w.get("name", ""),
            active=w.get("active", False),
            created_at=w.get("createdAt"),
            updated_at=w.get("updatedAt"),
            tags=[t.get("name", "") for t in w.get("tags", [])],
            nodes_count=len(w.get("nodes", [])),
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to activate workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/deactivate", response_model=WorkflowResponse)
async def deactivate_workflow(workflow_id: str):
    """Deactivate a workflow."""
    try:
        w = await n8n_client.activate_workflow(workflow_id, active=False)

        return WorkflowResponse(
            id=str(w.get("id", "")),
            name=w.get("name", ""),
            active=w.get("active", False),
            created_at=w.get("createdAt"),
            updated_at=w.get("updatedAt"),
            tags=[t.get("name", "") for t in w.get("tags", [])],
            nodes_count=len(w.get("nodes", [])),
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to deactivate workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(workflow_id: str | None = None, limit: int = 20):
    """List workflow executions."""
    try:
        result = await n8n_client.list_executions(workflow_id=workflow_id, limit=limit)
        executions = result.get("data", [])

        return ExecutionListResponse(
            executions=[
                ExecutionResponse(
                    id=str(e.get("id", "")),
                    workflow_id=str(e.get("workflowId", "")),
                    workflow_name=e.get("workflowData", {}).get("name") if e.get("workflowData") else None,
                    status=e.get("status", "unknown"),
                    started_at=e.get("startedAt"),
                    finished_at=e.get("stoppedAt"),
                    mode=e.get("mode"),
                )
                for e in executions
            ],
            total=len(executions),
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution(execution_id: str):
    """Get details of a specific execution."""
    try:
        e = await n8n_client.get_execution(execution_id)

        return ExecutionDetailResponse(
            id=str(e.get("id", "")),
            workflow_id=str(e.get("workflowId", "")),
            workflow_name=e.get("workflowData", {}).get("name") if e.get("workflowData") else None,
            status=e.get("status", "unknown"),
            started_at=e.get("startedAt"),
            finished_at=e.get("stoppedAt"),
            mode=e.get("mode"),
            data=e.get("data", {}),
            error=e.get("error", {}).get("message") if e.get("error") else None,
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials", response_model=CredentialListResponse)
async def list_credentials():
    """List all n8n credentials (without secrets)."""
    try:
        result = await n8n_client.list_credentials()
        credentials = result.get("data", [])

        return CredentialListResponse(
            credentials=[
                CredentialResponse(
                    id=str(c.get("id", "")),
                    name=c.get("name", ""),
                    type=c.get("type", ""),
                    created_at=c.get("createdAt"),
                    updated_at=c.get("updatedAt"),
                )
                for c in credentials
            ],
            total=len(credentials),
        )
    except N8NAPIKeyMissingError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))
