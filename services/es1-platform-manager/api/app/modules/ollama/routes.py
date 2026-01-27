"""API routes for Ollama integration - local LLM model management."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx

from app.core.config import settings

router = APIRouter(prefix="/ollama", tags=["Ollama"])

OLLAMA_URL = getattr(settings, 'OLLAMA_URL', 'http://es1-ollama:11434')


class ModelPullRequest(BaseModel):
    """Request to pull a model."""
    name: str
    insecure: bool = False


class GenerateRequest(BaseModel):
    """Request for text generation."""
    model: str
    prompt: str
    stream: bool = False
    options: Optional[dict] = None


class ChatMessage(BaseModel):
    """Chat message."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request for chat completion."""
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    options: Optional[dict] = None


# =============================================================================
# Model Management
# =============================================================================

@router.get("/models")
async def list_models():
    """List all locally available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama API error: {response.text}"
                )
            data = response.json()
            models = data.get("models", [])
            return {
                "models": [
                    {
                        "name": model.get("name"),
                        "model": model.get("model"),
                        "modified_at": model.get("modified_at"),
                        "size": model.get("size"),
                        "size_gb": round(model.get("size", 0) / (1024**3), 2),
                        "digest": model.get("digest"),
                        "details": model.get("details", {}),
                    }
                    for model in models
                ],
                "total": len(models),
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


@router.get("/models/{model_name}")
async def get_model_info(model_name: str):
    """Get detailed information about a specific model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/show",
                json={"name": model_name}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama API error: {response.text}"
                )
            data = response.json()
            return {
                "name": model_name,
                "modelfile": data.get("modelfile"),
                "parameters": data.get("parameters"),
                "template": data.get("template"),
                "details": data.get("details", {}),
                "model_info": data.get("model_info", {}),
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


@router.post("/models/pull")
async def pull_model(request: ModelPullRequest):
    """Pull/download a model from the Ollama library."""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:  # Long timeout for downloads
            response = await client.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": request.name, "insecure": request.insecure, "stream": False}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to pull model: {response.text}"
                )
            return {
                "message": f"Model '{request.name}' pulled successfully",
                "status": "completed",
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete a local model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{OLLAMA_URL}/api/delete",
                json={"name": model_name}
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to delete model: {response.text}"
                )
            return {
                "message": f"Model '{model_name}' deleted successfully",
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


@router.post("/models/{model_name}/copy")
async def copy_model(model_name: str, destination: str = Query(...)):
    """Copy a model to a new name."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/copy",
                json={"source": model_name, "destination": destination}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to copy model: {response.text}"
                )
            return {
                "message": f"Model '{model_name}' copied to '{destination}'",
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


# =============================================================================
# Inference
# =============================================================================

@router.post("/generate")
async def generate(request: GenerateRequest):
    """Generate text completion using a model."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": request.model,
                    "prompt": request.prompt,
                    "stream": False,
                    "options": request.options or {},
                }
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Generation failed: {response.text}"
                )
            data = response.json()
            return {
                "model": data.get("model"),
                "response": data.get("response"),
                "done": data.get("done"),
                "context": data.get("context"),
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "prompt_eval_duration": data.get("prompt_eval_duration"),
                "eval_count": data.get("eval_count"),
                "eval_duration": data.get("eval_duration"),
                # Calculate tokens per second
                "tokens_per_second": round(
                    data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9), 2
                ) if data.get("eval_duration") else None,
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat completion using a model."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": request.model,
                    "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                    "stream": False,
                    "options": request.options or {},
                }
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Chat failed: {response.text}"
                )
            data = response.json()
            return {
                "model": data.get("model"),
                "message": data.get("message"),
                "done": data.get("done"),
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "prompt_eval_duration": data.get("prompt_eval_duration"),
                "eval_count": data.get("eval_count"),
                "eval_duration": data.get("eval_duration"),
                "tokens_per_second": round(
                    data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9), 2
                ) if data.get("eval_duration") else None,
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


@router.post("/embeddings")
async def create_embeddings(model: str = Query(...), prompt: str = Query(...)):
    """Create embeddings for text."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": model, "prompt": prompt}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Embedding failed: {response.text}"
                )
            data = response.json()
            embedding = data.get("embedding", [])
            return {
                "model": model,
                "embedding": embedding,
                "dimensions": len(embedding),
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


# =============================================================================
# Running Models
# =============================================================================

@router.get("/ps")
async def list_running_models():
    """List currently loaded/running models."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/ps")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama API error: {response.text}"
                )
            data = response.json()
            models = data.get("models", [])
            return {
                "running_models": [
                    {
                        "name": model.get("name"),
                        "model": model.get("model"),
                        "size": model.get("size"),
                        "size_gb": round(model.get("size", 0) / (1024**3), 2),
                        "digest": model.get("digest"),
                        "details": model.get("details", {}),
                        "expires_at": model.get("expires_at"),
                        "size_vram": model.get("size_vram"),
                        "size_vram_gb": round(model.get("size_vram", 0) / (1024**3), 2) if model.get("size_vram") else None,
                    }
                    for model in models
                ],
                "total": len(models),
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def ollama_health():
    """Check Ollama server health."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/")
            is_healthy = response.status_code == 200

            # Also get running models count
            ps_response = await client.get(f"{OLLAMA_URL}/api/ps")
            running_count = len(ps_response.json().get("models", [])) if ps_response.status_code == 200 else 0

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "url": OLLAMA_URL,
                "running_models": running_count,
            }
    except httpx.RequestError as e:
        return {
            "status": "unavailable",
            "url": OLLAMA_URL,
            "error": str(e),
        }
