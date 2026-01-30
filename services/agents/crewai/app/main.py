"""
CrewAI Service for ES1 Platform
Provides API for creating and running CrewAI agent teams
"""

import os
import json
import logging
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

# Redis client
redis_client: Optional[redis.Redis] = None


async def register_template_agents():
    """Register template agents with the Agent Router"""
    templates = [
        {
            "name": "Researcher",
            "framework": "crewai",
            "description": "Senior Research Analyst - finds comprehensive and accurate information on given topics",
            "capabilities": ["research", "analysis", "information-gathering"],
            "metadata": {"template": "research_team", "role": "Senior Research Analyst"}
        },
        {
            "name": "Writer",
            "framework": "crewai",
            "description": "Content Writer - transforms research findings into clear, engaging content",
            "capabilities": ["writing", "content-creation", "documentation"],
            "metadata": {"template": "research_team", "role": "Content Writer"}
        },
        {
            "name": "Editor",
            "framework": "crewai",
            "description": "Editor - ensures content is polished, accurate, and well-structured",
            "capabilities": ["editing", "review", "quality-assurance"],
            "metadata": {"template": "research_team", "role": "Editor"}
        },
        {
            "name": "Code Reviewer",
            "framework": "crewai",
            "description": "Code Review Specialist - reviews code for quality, patterns, and best practices",
            "capabilities": ["code-review", "static-analysis", "best-practices"],
            "metadata": {"template": "code_review", "role": "Code Reviewer"}
        },
        {
            "name": "Security Analyst",
            "framework": "crewai",
            "description": "Security Analyst - identifies security vulnerabilities and risks in code",
            "capabilities": ["security-analysis", "vulnerability-detection", "risk-assessment"],
            "metadata": {"template": "code_review", "role": "Security Analyst"}
        },
        {
            "name": "Documentation Writer",
            "framework": "crewai",
            "description": "Documentation Writer - creates clear technical documentation",
            "capabilities": ["documentation", "technical-writing", "api-docs"],
            "metadata": {"template": "code_review", "role": "Documentation Writer"}
        },
        {
            "name": "Intake Specialist",
            "framework": "crewai",
            "description": "Intake Specialist - handles initial customer inquiries and routing",
            "capabilities": ["customer-intake", "triage", "routing"],
            "metadata": {"template": "customer_support", "role": "Intake Specialist"}
        },
        {
            "name": "Technical Support",
            "framework": "crewai",
            "description": "Technical Support Agent - resolves technical issues and provides solutions",
            "capabilities": ["technical-support", "troubleshooting", "problem-solving"],
            "metadata": {"template": "customer_support", "role": "Technical Support"}
        },
        {
            "name": "Quality Assurance",
            "framework": "crewai",
            "description": "QA Specialist - ensures support quality and customer satisfaction",
            "capabilities": ["quality-assurance", "feedback-analysis", "process-improvement"],
            "metadata": {"template": "customer_support", "role": "Quality Assurance"}
        },
    ]

    async with httpx.AsyncClient() as client:
        for agent in templates:
            try:
                response = await client.post(
                    f"{AGENT_ROUTER_URL}/agents/register",
                    json=agent,
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info(f"Registered agent: {agent['name']}")
                else:
                    logger.warning(f"Failed to register agent {agent['name']}: {response.status_code}")
            except Exception as e:
                logger.warning(f"Could not register agent {agent['name']} with router: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("CrewAI Service starting up...")

    # Register template agents with the router
    await register_template_agents()

    yield
    if redis_client:
        await redis_client.close()
    logger.info("CrewAI Service shutting down...")


app = FastAPI(
    title="CrewAI Service",
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

class AgentDefinition(BaseModel):
    """Definition of a CrewAI agent"""
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = Field(default_factory=list)
    llm_model: str = "llama3.2:3b"
    verbose: bool = True
    allow_delegation: bool = False
    max_iterations: int = 15


class TaskDefinition(BaseModel):
    """Definition of a task for an agent"""
    description: str
    agent_name: str
    expected_output: str
    context: Optional[List[str]] = None  # Names of tasks this depends on
    async_execution: bool = False


class CrewDefinition(BaseModel):
    """Definition of a CrewAI crew"""
    name: str
    description: str = ""
    agents: List[AgentDefinition]
    tasks: List[TaskDefinition]
    process: str = "sequential"  # sequential or hierarchical
    verbose: bool = True
    memory: bool = True
    manager_llm: Optional[str] = None  # Required for hierarchical


class CrewRunRequest(BaseModel):
    """Request to run a crew"""
    crew_id: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    callback_url: Optional[str] = None


class CrewRunResponse(BaseModel):
    """Response from running a crew"""
    run_id: str
    crew_id: str
    status: str
    started_at: str
    result: Optional[Any] = None
    error: Optional[str] = None


class AgentMessage(BaseModel):
    """Message for cross-agent communication"""
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "task"  # task, response, info
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== In-Memory Storage (for demo) ====================
# In production, use database

crews_storage: Dict[str, CrewDefinition] = {}
runs_storage: Dict[str, CrewRunResponse] = {}


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
        "service": "crewai",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== Crew Management ====================

@app.post("/crews", response_model=Dict[str, str])
async def create_crew(crew: CrewDefinition):
    """Create a new crew definition"""
    crew_id = f"crew_{crew.name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    crews_storage[crew_id] = crew

    # Store in Redis for persistence
    if redis_client:
        await redis_client.hset(
            "crewai:crews",
            crew_id,
            crew.model_dump_json()
        )

    logger.info(f"Created crew: {crew_id}")
    return {"crew_id": crew_id, "name": crew.name}


@app.get("/crews")
async def list_crews():
    """List all crews"""
    crews = []
    for crew_id, crew in crews_storage.items():
        crews.append({
            "crew_id": crew_id,
            "name": crew.name,
            "description": crew.description,
            "agent_count": len(crew.agents),
            "task_count": len(crew.tasks),
        })
    return {"crews": crews}


@app.get("/crews/{crew_id}")
async def get_crew(crew_id: str):
    """Get crew details"""
    if crew_id not in crews_storage:
        raise HTTPException(status_code=404, detail="Crew not found")
    return crews_storage[crew_id]


@app.delete("/crews/{crew_id}")
async def delete_crew(crew_id: str):
    """Delete a crew"""
    if crew_id not in crews_storage:
        raise HTTPException(status_code=404, detail="Crew not found")
    del crews_storage[crew_id]
    if redis_client:
        await redis_client.hdel("crewai:crews", crew_id)
    return {"deleted": crew_id}


# ==================== Crew Execution ====================

@app.post("/crews/{crew_id}/run", response_model=CrewRunResponse)
async def run_crew(crew_id: str, request: CrewRunRequest, background_tasks: BackgroundTasks):
    """Run a crew with given inputs"""
    if crew_id not in crews_storage:
        raise HTTPException(status_code=404, detail="Crew not found")

    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    run_response = CrewRunResponse(
        run_id=run_id,
        crew_id=crew_id,
        status="running",
        started_at=datetime.utcnow().isoformat(),
    )
    runs_storage[run_id] = run_response

    # Run crew in background
    background_tasks.add_task(
        execute_crew,
        run_id,
        crew_id,
        request.inputs,
        request.callback_url,
    )

    return run_response


async def execute_crew(
    run_id: str,
    crew_id: str,
    inputs: Dict[str, Any],
    callback_url: Optional[str],
):
    """Execute crew in background"""
    try:
        crew_def = crews_storage[crew_id]

        # Import crewai here to avoid startup issues if not installed
        from crewai import Agent, Task, Crew, Process
        from langchain_community.llms import Ollama

        # Create agents
        agents = {}
        for agent_def in crew_def.agents:
            llm = Ollama(
                model=agent_def.llm_model,
                base_url=OLLAMA_BASE_URL,
            )
            agents[agent_def.name] = Agent(
                role=agent_def.role,
                goal=agent_def.goal,
                backstory=agent_def.backstory,
                verbose=agent_def.verbose,
                allow_delegation=agent_def.allow_delegation,
                llm=llm,
            )

        # Create tasks
        tasks = []
        task_map = {}
        for task_def in crew_def.tasks:
            agent = agents.get(task_def.agent_name)
            if not agent:
                raise ValueError(f"Agent {task_def.agent_name} not found")

            context = []
            if task_def.context:
                for ctx_name in task_def.context:
                    if ctx_name in task_map:
                        context.append(task_map[ctx_name])

            task = Task(
                description=task_def.description,
                agent=agent,
                expected_output=task_def.expected_output,
                context=context if context else None,
                async_execution=task_def.async_execution,
            )
            tasks.append(task)
            task_map[task_def.description[:50]] = task

        # Create and run crew
        process = Process.sequential if crew_def.process == "sequential" else Process.hierarchical

        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=process,
            verbose=crew_def.verbose,
            memory=crew_def.memory,
        )

        # Publish start event
        if redis_client:
            await redis_client.publish(
                "agents:events",
                json.dumps({
                    "type": "crew_started",
                    "run_id": run_id,
                    "crew_id": crew_id,
                    "framework": "crewai",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )

        # Execute
        result = crew.kickoff(inputs=inputs)

        # Update run status
        runs_storage[run_id].status = "completed"
        runs_storage[run_id].result = str(result)

        # Publish completion event
        if redis_client:
            await redis_client.publish(
                "agents:events",
                json.dumps({
                    "type": "crew_completed",
                    "run_id": run_id,
                    "crew_id": crew_id,
                    "framework": "crewai",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )

        # Callback if provided
        if callback_url:
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json={
                    "run_id": run_id,
                    "status": "completed",
                    "result": str(result),
                })

        logger.info(f"Crew run completed: {run_id}")

    except Exception as e:
        logger.error(f"Crew run failed: {run_id} - {e}")
        runs_storage[run_id].status = "failed"
        runs_storage[run_id].error = str(e)

        if redis_client:
            await redis_client.publish(
                "agents:events",
                json.dumps({
                    "type": "crew_failed",
                    "run_id": run_id,
                    "crew_id": crew_id,
                    "framework": "crewai",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )


@app.get("/runs/{run_id}", response_model=CrewRunResponse)
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
    """Send a message to another agent (via Redis pub/sub)"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    message_data = {
        **message.model_dump(),
        "framework": "crewai",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Publish to agent-specific channel
    channel = f"agents:messages:{message.to_agent}"
    await redis_client.publish(channel, json.dumps(message_data))

    # Also publish to general channel
    await redis_client.publish("agents:messages", json.dumps(message_data))

    return {"status": "sent", "channel": channel}


@app.get("/messages/{agent_name}")
async def get_messages(agent_name: str, limit: int = 50):
    """Get recent messages for an agent from Redis list"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    key = f"agents:inbox:{agent_name}"
    messages = await redis_client.lrange(key, 0, limit - 1)
    return {"messages": [json.loads(m) for m in messages]}


# ==================== Templates ====================

@app.get("/templates")
async def list_templates():
    """List available crew templates"""
    return {
        "templates": [
            {
                "id": "research_team",
                "name": "Research Team",
                "description": "A team for researching topics and writing reports",
                "agents": ["Researcher", "Writer", "Editor"],
            },
            {
                "id": "code_review",
                "name": "Code Review Team",
                "description": "A team for reviewing and improving code",
                "agents": ["Code Reviewer", "Security Analyst", "Documentation Writer"],
            },
            {
                "id": "customer_support",
                "name": "Customer Support Team",
                "description": "A team for handling customer inquiries",
                "agents": ["Intake Specialist", "Technical Support", "Quality Assurance"],
            },
        ]
    }


@app.post("/templates/{template_id}/instantiate")
async def instantiate_template(template_id: str, customizations: Dict[str, Any] = None):
    """Create a crew from a template"""
    templates = {
        "research_team": CrewDefinition(
            name="Research Team",
            description="Research and report writing team",
            agents=[
                AgentDefinition(
                    name="Researcher",
                    role="Senior Research Analyst",
                    goal="Find comprehensive and accurate information on given topics",
                    backstory="You are an experienced researcher with a keen eye for detail and a talent for finding relevant information from various sources.",
                ),
                AgentDefinition(
                    name="Writer",
                    role="Content Writer",
                    goal="Transform research findings into clear, engaging content",
                    backstory="You are a skilled writer who excels at making complex topics accessible and engaging.",
                ),
                AgentDefinition(
                    name="Editor",
                    role="Editor",
                    goal="Ensure content is polished, accurate, and well-structured",
                    backstory="You are a meticulous editor with years of experience refining content for clarity and impact.",
                ),
            ],
            tasks=[
                TaskDefinition(
                    description="Research the given topic thoroughly",
                    agent_name="Researcher",
                    expected_output="Comprehensive research notes with key findings and sources",
                ),
                TaskDefinition(
                    description="Write a detailed report based on the research",
                    agent_name="Writer",
                    expected_output="Well-structured report draft",
                    context=["Research the given topic thoroughly"],
                ),
                TaskDefinition(
                    description="Review and polish the report",
                    agent_name="Editor",
                    expected_output="Final polished report ready for publication",
                    context=["Write a detailed report based on the research"],
                ),
            ],
            process="sequential",
        ),
    }

    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")

    crew = templates[template_id]

    # Apply customizations
    if customizations:
        if "name" in customizations:
            crew.name = customizations["name"]
        if "description" in customizations:
            crew.description = customizations["description"]

    # Create the crew
    return await create_crew(crew)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
