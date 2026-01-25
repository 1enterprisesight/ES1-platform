"""API routes for the Langflow module."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.events import event_bus, EventType
from .client import langflow_client
from .services import langflow_discovery
from .schemas import (
    FlowResponse,
    FlowListResponse,
    FlowCreateRequest,
    RunFlowRequest,
    FlowRunResponse,
    LangflowHealthResponse,
    DiscoveryResultResponse,
)

router = APIRouter(prefix="/langflow", tags=["Langflow"])


@router.get("/health", response_model=LangflowHealthResponse)
async def get_langflow_health():
    """Check Langflow health status."""
    result = await langflow_client.health_check()
    return LangflowHealthResponse(
        status=result.get("status", "unknown"),
        message=result.get("message") or result.get("error"),
    )


@router.get("/flows", response_model=FlowListResponse)
async def list_flows():
    """List all flows from Langflow."""
    try:
        flows = await langflow_client.list_flows()
        return FlowListResponse(
            flows=[
                FlowResponse(
                    id=f.get("id", ""),
                    name=f.get("name", "Unnamed"),
                    description=f.get("description"),
                    endpoint_name=f.get("endpoint_name"),
                    is_component=f.get("is_component", False),
                    updated_at=f.get("updated_at"),
                    folder_id=f.get("folder_id"),
                )
                for f in flows
            ],
            total=len(flows),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flows/{flow_id}", response_model=FlowResponse)
async def get_flow(flow_id: str):
    """Get details of a specific flow."""
    try:
        f = await langflow_client.get_flow(flow_id)
        return FlowResponse(
            id=f.get("id", flow_id),
            name=f.get("name", "Unnamed"),
            description=f.get("description"),
            endpoint_name=f.get("endpoint_name"),
            is_component=f.get("is_component", False),
            updated_at=f.get("updated_at"),
            folder_id=f.get("folder_id"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flows", response_model=FlowResponse)
async def create_flow(request: FlowCreateRequest):
    """Create a new flow."""
    try:
        f = await langflow_client.create_flow(
            name=request.name,
            description=request.description,
            data=request.data,
        )

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "create_flow",
                "flow_id": f.get("id"),
                "name": request.name,
                "message": f"Flow '{request.name}' created successfully",
            },
        )

        return FlowResponse(
            id=f.get("id", ""),
            name=f.get("name", request.name),
            description=f.get("description"),
            endpoint_name=f.get("endpoint_name"),
            is_component=f.get("is_component", False),
            updated_at=f.get("updated_at"),
            folder_id=f.get("folder_id"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/flows/{flow_id}")
async def delete_flow(flow_id: str):
    """Delete a flow."""
    try:
        await langflow_client.delete_flow(flow_id)

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "delete_flow",
                "flow_id": flow_id,
                "message": f"Flow {flow_id} deleted successfully",
            },
        )

        return {"message": "Flow deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flows/{flow_id}/run", response_model=FlowRunResponse)
async def run_flow(flow_id: str, request: RunFlowRequest):
    """Run a flow with input."""
    try:
        await event_bus.publish(
            EventType.OPERATION_STARTED,
            {
                "operation": "run_flow",
                "flow_id": flow_id,
                "message": f"Running flow {flow_id}...",
            },
        )

        result = await langflow_client.run_flow(
            flow_id=flow_id,
            input_value=request.input_value,
            input_type=request.input_type,
            output_type=request.output_type,
            tweaks=request.tweaks,
            session_id=request.session_id,
        )

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "run_flow",
                "flow_id": flow_id,
                "message": "Flow execution completed",
            },
        )

        return FlowRunResponse(
            outputs=result.get("outputs", []),
            session_id=result.get("session_id"),
        )
    except Exception as e:
        await event_bus.publish(
            EventType.OPERATION_FAILED,
            {
                "operation": "run_flow",
                "flow_id": flow_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover", response_model=DiscoveryResultResponse)
async def discover_resources(db: AsyncSession = Depends(get_db)):
    """Discover all resources from Langflow and sync to database."""
    try:
        await event_bus.publish(
            EventType.OPERATION_STARTED,
            {
                "operation": "langflow_discovery",
                "message": "Starting Langflow resource discovery...",
            },
        )

        result = await langflow_discovery.discover_all(db)

        flows_count = len(result.get("flows", []))

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "langflow_discovery",
                "flows_discovered": flows_count,
                "message": f"Discovered {flows_count} flows",
            },
        )

        return DiscoveryResultResponse(
            flows_discovered=flows_count,
            message=f"Successfully discovered {flows_count} flows",
        )
    except Exception as e:
        await event_bus.publish(
            EventType.OPERATION_FAILED,
            {
                "operation": "langflow_discovery",
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components")
async def get_components():
    """Get available Langflow components."""
    try:
        components = await langflow_client.get_components()
        return components
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
