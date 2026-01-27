"""
Agent Router for ES1 Platform
Unified API for routing requests to agent frameworks (CrewAI, AutoGen, Langflow, n8n)
Provides agent registry, cross-framework messaging, and shared context management
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis.asyncio as redis
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CREWAI_URL = os.getenv("CREWAI_URL", "http://crewai:8100")
AUTOGEN_URL = os.getenv("AUTOGEN_URL", "http://autogen:8101")
LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://langflow:7860")
N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")
AIML_DB_URL = os.getenv("AIML_DB_URL", "postgresql://aiml_user:aiml_dev_password@aiml-postgres:5432/aiml")

# Redis client
redis_client: Optional[redis.Redis] = None

# HTTP client for service calls
http_client: Optional[httpx.AsyncClient] = None

# WebSocket connections for real-time updates
websocket_connections: List[WebSocket] = []


class AgentFramework(str, Enum):
    """Supported agent frameworks"""
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    LANGFLOW = "langflow"
    N8N = "n8n"


FRAMEWORK_URLS = {
    AgentFramework.CREWAI: CREWAI_URL,
    AgentFramework.AUTOGEN: AUTOGEN_URL,
    AgentFramework.LANGFLOW: LANGFLOW_URL,
    AgentFramework.N8N: N8N_URL,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global redis_client, http_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    http_client = httpx.AsyncClient(timeout=60.0)

    # Start event listener
    asyncio.create_task(event_listener())

    logger.info("Agent Router starting up...")
    yield

    if redis_client:
        await redis_client.close()
    if http_client:
        await http_client.aclose()
    logger.info("Agent Router shutting down...")


app = FastAPI(
    title="Agent Router",
    description="ES1 Platform Unified Agent API - Routes to CrewAI, AutoGen, Langflow, n8n",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Pydantic Models ====================

class AgentRegistration(BaseModel):
    """Registration of an agent in the router"""
    name: str
    framework: AgentFramework
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """A task to route to an agent"""
    task_type: str  # "crew_run", "conversation", "flow", "workflow"
    agent_name: Optional[str] = None
    framework: Optional[AgentFramework] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    callback_url: Optional[str] = None


class TaskResponse(BaseModel):
    """Response from task submission"""
    task_id: str
    framework: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class CrossAgentMessage(BaseModel):
    """Message between agents across frameworks"""
    from_agent: str
    from_framework: AgentFramework
    to_agent: str
    to_framework: Optional[AgentFramework] = None  # None = broadcast
    content: str
    message_type: str = "task"  # task, response, info, event
    priority: int = 5  # 1-10, higher = more urgent
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextEntry(BaseModel):
    """Shared context entry"""
    key: str
    value: Any
    scope: str = "global"  # global, session, agent
    ttl_seconds: Optional[int] = None


class AgentEvent(BaseModel):
    """Event from an agent"""
    event_type: str
    framework: AgentFramework
    agent_name: Optional[str] = None
    run_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ==================== Agent Registry ====================

@app.get("/health")
async def health_check():
    """Health check with service connectivity"""
    services = {}

    for framework, url in FRAMEWORK_URLS.items():
        try:
            response = await http_client.get(f"{url}/health", timeout=5.0)
            services[framework.value] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services[framework.value] = "unreachable"

    redis_ok = False
    try:
        if redis_client:
            await redis_client.ping()
            redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "agent-router",
        "redis": "connected" if redis_ok else "disconnected",
        "frameworks": services,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/agents/register")
async def register_agent(registration: AgentRegistration):
    """Register an agent with the router"""
    agent_key = f"{registration.framework.value}:{registration.name}"

    agent_data = {
        **registration.model_dump(),
        "registered_at": datetime.utcnow().isoformat(),
        "last_seen": datetime.utcnow().isoformat(),
    }

    if redis_client:
        await redis_client.hset("agents:registry", agent_key, json.dumps(agent_data))

    logger.info(f"Registered agent: {agent_key}")
    return {"agent_key": agent_key, "status": "registered"}


@app.get("/agents")
async def list_agents(framework: Optional[AgentFramework] = None):
    """List all registered agents"""
    agents = []

    if redis_client:
        registry = await redis_client.hgetall("agents:registry")
        for key, value in registry.items():
            agent_data = json.loads(value)
            if framework is None or agent_data.get("framework") == framework.value:
                agents.append({"key": key, **agent_data})

    return {"agents": agents}


@app.get("/agents/{agent_key}")
async def get_agent(agent_key: str):
    """Get agent details"""
    if redis_client:
        data = await redis_client.hget("agents:registry", agent_key)
        if data:
            return json.loads(data)

    raise HTTPException(status_code=404, detail="Agent not found")


@app.delete("/agents/{agent_key}")
async def unregister_agent(agent_key: str):
    """Unregister an agent"""
    if redis_client:
        await redis_client.hdel("agents:registry", agent_key)
    return {"status": "unregistered", "agent_key": agent_key}


# ==================== Task Routing ====================

@app.post("/tasks", response_model=TaskResponse)
async def submit_task(task: AgentTask):
    """Submit a task to be routed to the appropriate agent/framework"""
    task_id = f"task_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    # Determine framework
    framework = task.framework
    if not framework and task.agent_name:
        # Look up agent in registry
        if redis_client:
            registry = await redis_client.hgetall("agents:registry")
            for key, value in registry.items():
                agent_data = json.loads(value)
                if agent_data.get("name") == task.agent_name:
                    framework = AgentFramework(agent_data.get("framework"))
                    break

    if not framework:
        # Default routing based on task type
        if task.task_type == "crew_run":
            framework = AgentFramework.CREWAI
        elif task.task_type == "conversation":
            framework = AgentFramework.AUTOGEN
        elif task.task_type == "flow":
            framework = AgentFramework.LANGFLOW
        elif task.task_type == "workflow":
            framework = AgentFramework.N8N
        else:
            raise HTTPException(status_code=400, detail="Cannot determine target framework")

    # Route to framework
    base_url = FRAMEWORK_URLS[framework]

    try:
        if framework == AgentFramework.CREWAI:
            # Route to CrewAI
            response = await http_client.post(
                f"{base_url}/crews/{task.inputs.get('crew_id', 'default')}/run",
                json={
                    "crew_id": task.inputs.get("crew_id"),
                    "inputs": task.inputs,
                    "callback_url": task.callback_url,
                }
            )
            result = response.json()
            return TaskResponse(
                task_id=task_id,
                framework=framework.value,
                status="submitted",
                details=result,
            )

        elif framework == AgentFramework.AUTOGEN:
            # Route to AutoGen
            response = await http_client.post(
                f"{base_url}/conversations/{task.inputs.get('conversation_id', 'default')}/run",
                json={
                    "conversation_id": task.inputs.get("conversation_id"),
                    "initial_message": task.inputs.get("message", ""),
                    "context": task.context,
                    "callback_url": task.callback_url,
                }
            )
            result = response.json()
            return TaskResponse(
                task_id=task_id,
                framework=framework.value,
                status="submitted",
                details=result,
            )

        elif framework == AgentFramework.LANGFLOW:
            # Route to Langflow
            flow_id = task.inputs.get("flow_id")
            response = await http_client.post(
                f"{base_url}/api/v1/run/{flow_id}",
                json={"inputs": task.inputs}
            )
            result = response.json()
            return TaskResponse(
                task_id=task_id,
                framework=framework.value,
                status="submitted",
                details=result,
            )

        elif framework == AgentFramework.N8N:
            # Route to n8n webhook
            webhook_path = task.inputs.get("webhook_path", "/webhook/agent-task")
            response = await http_client.post(
                f"{base_url}{webhook_path}",
                json=task.inputs,
            )
            return TaskResponse(
                task_id=task_id,
                framework=framework.value,
                status="submitted",
                details={"response": response.text},
            )

    except httpx.RequestError as e:
        logger.error(f"Failed to route task: {e}")
        raise HTTPException(status_code=503, detail=f"Framework {framework.value} unavailable")

    raise HTTPException(status_code=400, detail="Invalid task configuration")


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status (checks all frameworks)"""
    # This would query the frameworks for run status
    # For now, return from Redis if we stored it
    if redis_client:
        status = await redis_client.hget("tasks:status", task_id)
        if status:
            return json.loads(status)

    raise HTTPException(status_code=404, detail="Task not found")


# ==================== Cross-Framework Messaging ====================

@app.post("/messages")
async def send_cross_framework_message(message: CrossAgentMessage):
    """Send a message between agents (potentially across frameworks)"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    message_data = {
        **message.model_dump(),
        "message_id": f"msg_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Publish to target agent's channel
    if message.to_framework:
        channel = f"agents:messages:{message.to_framework.value}:{message.to_agent}"
    else:
        channel = f"agents:messages:{message.to_agent}"

    await redis_client.publish(channel, json.dumps(message_data))

    # Also publish to general channel for monitoring
    await redis_client.publish("agents:messages", json.dumps(message_data))

    # Store in inbox for retrieval
    inbox_key = f"agents:inbox:{message.to_agent}"
    await redis_client.lpush(inbox_key, json.dumps(message_data))
    await redis_client.ltrim(inbox_key, 0, 99)  # Keep last 100 messages

    return {"status": "sent", "message_id": message_data["message_id"]}


@app.get("/messages/{agent_name}")
async def get_agent_messages(agent_name: str, limit: int = 50):
    """Get messages for an agent"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    inbox_key = f"agents:inbox:{agent_name}"
    messages = await redis_client.lrange(inbox_key, 0, limit - 1)
    return {"messages": [json.loads(m) for m in messages]}


# ==================== Shared Context Store ====================

@app.post("/context")
async def set_context(entry: ContextEntry):
    """Set a shared context entry"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    key = f"agents:context:{entry.scope}:{entry.key}"
    value = json.dumps(entry.value) if not isinstance(entry.value, str) else entry.value

    if entry.ttl_seconds:
        await redis_client.setex(key, entry.ttl_seconds, value)
    else:
        await redis_client.set(key, value)

    return {"status": "set", "key": entry.key, "scope": entry.scope}


@app.get("/context/{scope}/{key}")
async def get_context(scope: str, key: str):
    """Get a shared context entry"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    redis_key = f"agents:context:{scope}:{key}"
    value = await redis_client.get(redis_key)

    if value is None:
        raise HTTPException(status_code=404, detail="Context entry not found")

    try:
        return {"key": key, "scope": scope, "value": json.loads(value)}
    except json.JSONDecodeError:
        return {"key": key, "scope": scope, "value": value}


@app.delete("/context/{scope}/{key}")
async def delete_context(scope: str, key: str):
    """Delete a shared context entry"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    redis_key = f"agents:context:{scope}:{key}"
    await redis_client.delete(redis_key)
    return {"status": "deleted", "key": key, "scope": scope}


@app.get("/context/{scope}")
async def list_context(scope: str):
    """List all context entries in a scope"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    pattern = f"agents:context:{scope}:*"
    keys = []
    async for key in redis_client.scan_iter(match=pattern):
        short_key = key.split(":")[-1]
        keys.append(short_key)

    return {"scope": scope, "keys": keys}


# ==================== Event Streaming ====================

async def event_listener():
    """Listen for agent events and broadcast to WebSocket clients"""
    if not redis_client:
        return

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("agents:events", "agents:messages")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                # Broadcast to all connected WebSocket clients
                for ws in websocket_connections:
                    try:
                        await ws.send_text(data)
                    except Exception:
                        pass
    except Exception as e:
        logger.error(f"Event listener error: {e}")
    finally:
        await pubsub.unsubscribe()


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time agent events"""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Could handle client commands here
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)


# ==================== Framework Status ====================

@app.get("/frameworks")
async def list_frameworks():
    """List all supported frameworks and their status"""
    frameworks = []

    for framework in AgentFramework:
        url = FRAMEWORK_URLS[framework]
        status = "unknown"

        try:
            response = await http_client.get(f"{url}/health", timeout=5.0)
            if response.status_code == 200:
                status = "healthy"
                health_data = response.json()
            else:
                status = "unhealthy"
                health_data = {}
        except Exception as e:
            status = "unreachable"
            health_data = {"error": str(e)}

        frameworks.append({
            "name": framework.value,
            "url": url,
            "status": status,
            "health": health_data,
        })

    return {"frameworks": frameworks}


@app.get("/frameworks/{framework}/agents")
async def list_framework_agents(framework: AgentFramework):
    """List agents/resources from a specific framework"""
    url = FRAMEWORK_URLS[framework]

    try:
        if framework == AgentFramework.CREWAI:
            response = await http_client.get(f"{url}/crews")
            return response.json()
        elif framework == AgentFramework.AUTOGEN:
            response = await http_client.get(f"{url}/conversations")
            return response.json()
        elif framework == AgentFramework.LANGFLOW:
            response = await http_client.get(f"{url}/api/v1/flows")
            return response.json()
        elif framework == AgentFramework.N8N:
            # n8n requires authentication, return placeholder
            return {"workflows": [], "note": "n8n requires authentication"}
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Framework {framework.value} unavailable: {e}")


# ==================== Agent Networks ====================

class AgentNetwork(BaseModel):
    """Definition of an agent network spanning frameworks"""
    name: str
    description: str = ""
    agents: List[Dict[str, Any]]  # List of agent references
    connections: List[Dict[str, str]] = Field(default_factory=list)  # Agent connections
    orchestration: str = "event_driven"  # event_driven, sequential, parallel


@app.post("/networks")
async def create_network(network: AgentNetwork):
    """Create an agent network"""
    network_id = f"net_{network.name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    if redis_client:
        await redis_client.hset(
            "agents:networks",
            network_id,
            network.model_dump_json()
        )

    return {"network_id": network_id, "name": network.name}


@app.get("/networks")
async def list_networks():
    """List all agent networks"""
    networks = []
    if redis_client:
        data = await redis_client.hgetall("agents:networks")
        for net_id, value in data.items():
            network = json.loads(value)
            networks.append({"network_id": net_id, **network})
    return {"networks": networks}


@app.get("/networks/{network_id}")
async def get_network(network_id: str):
    """Get network details"""
    if redis_client:
        data = await redis_client.hget("agents:networks", network_id)
        if data:
            return {"network_id": network_id, **json.loads(data)}
    raise HTTPException(status_code=404, detail="Network not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8102)
