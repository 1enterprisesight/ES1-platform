"""
AutoGen Service for ES1 Platform
Provides API for creating and running AutoGen multi-agent conversations
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis.asyncio as redis
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
AGENT_ROUTER_URL = os.getenv("AGENT_ROUTER_URL", "http://agent-router:8102")

# Registration retry settings
REGISTRATION_MAX_RETRIES = 10
REGISTRATION_RETRY_DELAY = 3  # seconds

# Redis client
redis_client: Optional[redis.Redis] = None


async def register_template_agents():
    """Register template agents with the Agent Router (with retry logic)"""
    templates = [
        {
            "name": "Code Assistant",
            "framework": "autogen",
            "description": "AI coding assistant that helps with coding tasks, explains code, debugs issues, and suggests improvements",
            "capabilities": ["coding", "debugging", "code-explanation", "refactoring"],
            "metadata": {"template": "code_assistant", "agent_type": "assistant"}
        },
        {
            "name": "User Proxy",
            "framework": "autogen",
            "description": "User proxy agent that represents human input in conversations",
            "capabilities": ["user-interaction", "task-initiation", "feedback"],
            "metadata": {"template": "code_assistant", "agent_type": "user_proxy"}
        },
        {
            "name": "Proponent",
            "framework": "autogen",
            "description": "Debate agent that argues in favor of topics with strong arguments and evidence",
            "capabilities": ["argumentation", "persuasion", "evidence-presentation"],
            "metadata": {"template": "debate", "agent_type": "assistant"}
        },
        {
            "name": "Opponent",
            "framework": "autogen",
            "description": "Debate agent that argues against topics with counterarguments and challenges",
            "capabilities": ["counterargument", "critical-analysis", "rebuttal"],
            "metadata": {"template": "debate", "agent_type": "assistant"}
        },
        {
            "name": "Moderator",
            "framework": "autogen",
            "description": "Debate moderator that ensures fair discussion, summarizes points, and declares conclusions",
            "capabilities": ["moderation", "summarization", "decision-making"],
            "metadata": {"template": "debate", "agent_type": "assistant"}
        },
        {
            "name": "Ideator",
            "framework": "autogen",
            "description": "Brainstorming agent that generates creative ideas and possibilities",
            "capabilities": ["ideation", "creativity", "brainstorming"],
            "metadata": {"template": "brainstorm", "agent_type": "assistant"}
        },
        {
            "name": "Critic",
            "framework": "autogen",
            "description": "Critical analysis agent that evaluates ideas and identifies potential issues",
            "capabilities": ["critical-thinking", "evaluation", "risk-analysis"],
            "metadata": {"template": "brainstorm", "agent_type": "assistant"}
        },
        {
            "name": "Synthesizer",
            "framework": "autogen",
            "description": "Synthesis agent that combines ideas into cohesive solutions",
            "capabilities": ["synthesis", "integration", "solution-design"],
            "metadata": {"template": "brainstorm", "agent_type": "assistant"}
        },
    ]

    # Wait for agent-router to be available with retries
    router_available = False
    for attempt in range(REGISTRATION_MAX_RETRIES):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{AGENT_ROUTER_URL}/health", timeout=5.0)
                if response.status_code == 200:
                    router_available = True
                    logger.info(f"Agent router available after {attempt + 1} attempt(s)")
                    break
        except Exception as e:
            logger.info(f"Waiting for agent-router (attempt {attempt + 1}/{REGISTRATION_MAX_RETRIES}): {e}")
            await asyncio.sleep(REGISTRATION_RETRY_DELAY)

    if not router_available:
        logger.error("Agent router not available after maximum retries, skipping agent registration")
        return

    # Register all agents
    async with httpx.AsyncClient() as client:
        registered_count = 0
        for agent in templates:
            try:
                response = await client.post(
                    f"{AGENT_ROUTER_URL}/agents/register",
                    json=agent,
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info(f"Registered agent: {agent['name']}")
                    registered_count += 1
                else:
                    logger.warning(f"Failed to register agent {agent['name']}: {response.status_code}")
            except Exception as e:
                logger.warning(f"Could not register agent {agent['name']} with router: {e}")

        logger.info(f"AutoGen agent registration complete: {registered_count}/{len(templates)} agents registered")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("AutoGen Service starting up...")

    # Register template agents with the router
    await register_template_agents()

    yield
    if redis_client:
        await redis_client.close()
    logger.info("AutoGen Service shutting down...")


app = FastAPI(
    title="AutoGen Service",
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

class AgentConfig(BaseModel):
    """Configuration for an AutoGen agent"""
    name: str
    system_message: str
    description: str = ""
    agent_type: str = "assistant"  # assistant, user_proxy, group_chat_manager
    llm_model: str = "llama3.2:3b"
    human_input_mode: str = "NEVER"  # NEVER, ALWAYS, TERMINATE
    max_consecutive_auto_reply: int = 10
    code_execution: bool = False


class ConversationConfig(BaseModel):
    """Configuration for an AutoGen conversation"""
    name: str
    description: str = ""
    agents: List[AgentConfig]
    initiator_agent: str  # Name of agent that initiates
    max_turns: int = 10
    use_group_chat: bool = False
    group_chat_speaker_selection: str = "auto"  # auto, round_robin, random


class ConversationRunRequest(BaseModel):
    """Request to run a conversation"""
    conversation_id: str
    initial_message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    callback_url: Optional[str] = None


class ConversationRunResponse(BaseModel):
    """Response from running a conversation"""
    run_id: str
    conversation_id: str
    status: str
    started_at: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None


class AgentMessage(BaseModel):
    """Message for cross-agent communication"""
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "chat"
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== In-Memory Storage ====================

conversations_storage: Dict[str, ConversationConfig] = {}
runs_storage: Dict[str, ConversationRunResponse] = {}


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_ok = False
    try:
        if redis_client:
            await redis_client.ping()
            redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "autogen",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== Conversation Management ====================

@app.post("/conversations", response_model=Dict[str, str])
async def create_conversation(config: ConversationConfig):
    """Create a new conversation configuration"""
    conv_id = f"conv_{config.name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    conversations_storage[conv_id] = config

    # Store in Redis
    if redis_client:
        await redis_client.hset(
            "autogen:conversations",
            conv_id,
            config.model_dump_json()
        )

    logger.info(f"Created conversation: {conv_id}")
    return {"conversation_id": conv_id, "name": config.name}


@app.get("/conversations")
async def list_conversations():
    """List all conversations"""
    convs = []
    for conv_id, config in conversations_storage.items():
        convs.append({
            "conversation_id": conv_id,
            "name": config.name,
            "description": config.description,
            "agent_count": len(config.agents),
            "use_group_chat": config.use_group_chat,
        })
    return {"conversations": convs}


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation details"""
    if conversation_id not in conversations_storage:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversations_storage[conversation_id]


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id not in conversations_storage:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del conversations_storage[conversation_id]
    if redis_client:
        await redis_client.hdel("autogen:conversations", conversation_id)
    return {"deleted": conversation_id}


# ==================== Conversation Execution ====================

@app.post("/conversations/{conversation_id}/run", response_model=ConversationRunResponse)
async def run_conversation(
    conversation_id: str,
    request: ConversationRunRequest,
    background_tasks: BackgroundTasks
):
    """Run a conversation with given initial message"""
    if conversation_id not in conversations_storage:
        raise HTTPException(status_code=404, detail="Conversation not found")

    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    run_response = ConversationRunResponse(
        run_id=run_id,
        conversation_id=conversation_id,
        status="running",
        started_at=datetime.utcnow().isoformat(),
    )
    runs_storage[run_id] = run_response

    # Run conversation in background
    background_tasks.add_task(
        execute_conversation,
        run_id,
        conversation_id,
        request.initial_message,
        request.context,
        request.callback_url,
    )

    return run_response


async def execute_conversation(
    run_id: str,
    conversation_id: str,
    initial_message: str,
    context: Dict[str, Any],
    callback_url: Optional[str],
):
    """Execute conversation in background"""
    try:
        config = conversations_storage[conversation_id]

        # Import autogen here to avoid startup issues
        import autogen

        # Configure LLM
        llm_config = {
            "config_list": [
                {
                    "model": config.agents[0].llm_model if config.agents else "llama3.2:3b",
                    "base_url": f"{OLLAMA_BASE_URL}/v1",
                    "api_key": "ollama",  # Required but not used
                }
            ],
            "timeout": 120,
        }

        # Create agents
        agents = {}
        for agent_config in config.agents:
            if agent_config.agent_type == "assistant":
                agents[agent_config.name] = autogen.AssistantAgent(
                    name=agent_config.name,
                    system_message=agent_config.system_message,
                    llm_config=llm_config,
                    max_consecutive_auto_reply=agent_config.max_consecutive_auto_reply,
                )
            elif agent_config.agent_type == "user_proxy":
                agents[agent_config.name] = autogen.UserProxyAgent(
                    name=agent_config.name,
                    system_message=agent_config.system_message,
                    human_input_mode=agent_config.human_input_mode,
                    max_consecutive_auto_reply=agent_config.max_consecutive_auto_reply,
                    code_execution_config={"use_docker": False} if agent_config.code_execution else False,
                )

        # Publish start event
        if redis_client:
            await redis_client.publish(
                "agents:events",
                json.dumps({
                    "type": "conversation_started",
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    "framework": "autogen",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )

        # Run conversation
        initiator = agents.get(config.initiator_agent)
        if not initiator:
            raise ValueError(f"Initiator agent {config.initiator_agent} not found")

        if config.use_group_chat and len(agents) > 2:
            # Group chat
            groupchat = autogen.GroupChat(
                agents=list(agents.values()),
                messages=[],
                max_round=config.max_turns,
                speaker_selection_method=config.group_chat_speaker_selection,
            )
            manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

            # Start chat
            initiator.initiate_chat(
                manager,
                message=initial_message,
            )

            # Collect messages
            messages = [
                {"role": m.get("role", ""), "name": m.get("name", ""), "content": m.get("content", "")}
                for m in groupchat.messages
            ]
        else:
            # Two-agent conversation
            other_agents = [a for name, a in agents.items() if name != config.initiator_agent]
            if other_agents:
                recipient = other_agents[0]
                initiator.initiate_chat(
                    recipient,
                    message=initial_message,
                    max_turns=config.max_turns,
                )

                # Collect messages from chat history
                messages = []
                for msg in initiator.chat_messages.get(recipient, []):
                    messages.append({
                        "role": msg.get("role", ""),
                        "name": msg.get("name", ""),
                        "content": msg.get("content", ""),
                    })

        # Update run status
        runs_storage[run_id].status = "completed"
        runs_storage[run_id].messages = messages
        runs_storage[run_id].result = messages[-1]["content"] if messages else None

        # Publish completion event
        if redis_client:
            await redis_client.publish(
                "agents:events",
                json.dumps({
                    "type": "conversation_completed",
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    "framework": "autogen",
                    "message_count": len(messages),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )

        # Callback if provided
        if callback_url:
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json={
                    "run_id": run_id,
                    "status": "completed",
                    "messages": messages,
                })

        logger.info(f"Conversation completed: {run_id}")

    except Exception as e:
        logger.error(f"Conversation failed: {run_id} - {e}")
        runs_storage[run_id].status = "failed"
        runs_storage[run_id].error = str(e)

        if redis_client:
            await redis_client.publish(
                "agents:events",
                json.dumps({
                    "type": "conversation_failed",
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    "framework": "autogen",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )


@app.get("/runs/{run_id}", response_model=ConversationRunResponse)
async def get_run(run_id: str):
    """Get run status"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs_storage[run_id]


@app.get("/runs")
async def list_runs(limit: int = 20):
    """List recent runs"""
    runs = list(runs_storage.values())[-limit:]
    return {"runs": runs}


# ==================== Cross-Agent Messaging ====================

@app.post("/messages")
async def send_message(message: AgentMessage):
    """Send a message to another agent"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    message_data = {
        **message.model_dump(),
        "framework": "autogen",
        "timestamp": datetime.utcnow().isoformat(),
    }

    channel = f"agents:messages:{message.to_agent}"
    await redis_client.publish(channel, json.dumps(message_data))
    await redis_client.publish("agents:messages", json.dumps(message_data))

    return {"status": "sent", "channel": channel}


# ==================== Templates ====================

@app.get("/templates")
async def list_templates():
    """List available conversation templates"""
    return {
        "templates": [
            {
                "id": "code_assistant",
                "name": "Code Assistant",
                "description": "An AI assistant that helps with coding tasks",
                "agents": ["Assistant", "User"],
            },
            {
                "id": "debate",
                "name": "Debate",
                "description": "Two agents debating a topic",
                "agents": ["Proponent", "Opponent", "Moderator"],
            },
            {
                "id": "brainstorm",
                "name": "Brainstorming Session",
                "description": "Multiple agents brainstorming ideas",
                "agents": ["Ideator", "Critic", "Synthesizer"],
            },
        ]
    }


@app.post("/templates/{template_id}/instantiate")
async def instantiate_template(template_id: str, customizations: Dict[str, Any] = None):
    """Create a conversation from a template"""
    templates = {
        "code_assistant": ConversationConfig(
            name="Code Assistant",
            description="AI coding assistant conversation",
            agents=[
                AgentConfig(
                    name="Assistant",
                    system_message="You are a helpful AI assistant that helps with coding tasks. You can explain code, debug issues, and suggest improvements.",
                    agent_type="assistant",
                ),
                AgentConfig(
                    name="User",
                    system_message="You are a user asking questions about code.",
                    agent_type="user_proxy",
                    human_input_mode="NEVER",
                ),
            ],
            initiator_agent="User",
            max_turns=10,
        ),
        "debate": ConversationConfig(
            name="Debate",
            description="Multi-agent debate on a topic",
            agents=[
                AgentConfig(
                    name="Proponent",
                    system_message="You argue in favor of the topic. Present strong arguments and evidence.",
                    agent_type="assistant",
                ),
                AgentConfig(
                    name="Opponent",
                    system_message="You argue against the topic. Present counterarguments and challenge the proponent.",
                    agent_type="assistant",
                ),
                AgentConfig(
                    name="Moderator",
                    system_message="You moderate the debate. Ensure fair discussion, summarize points, and declare a conclusion.",
                    agent_type="assistant",
                ),
            ],
            initiator_agent="Moderator",
            max_turns=12,
            use_group_chat=True,
            group_chat_speaker_selection="auto",
        ),
    }

    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")

    config = templates[template_id]

    if customizations:
        if "name" in customizations:
            config.name = customizations["name"]
        if "description" in customizations:
            config.description = customizations["description"]

    return await create_conversation(config)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8101)
