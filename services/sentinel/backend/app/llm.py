from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.config import GEMINI_API_KEY, GCP_PROJECT, GCP_LOCATION, GEMINI_MODEL

logger = logging.getLogger(__name__)

LLM_TIMEOUT = 45  # seconds — prevent hung LLM calls from blocking the server

_model = None
_backend = None  # "genai" or "vertexai"
_executor = ThreadPoolExecutor(max_workers=3)

# Langfuse tracing (optional — degrades gracefully)
_langfuse = None
try:
    langfuse_url = os.environ.get("LANGFUSE_URL")
    langfuse_pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
    langfuse_sk = os.environ.get("LANGFUSE_SECRET_KEY")
    if langfuse_url and langfuse_pk and langfuse_sk:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=langfuse_pk,
            secret_key=langfuse_sk,
            host=langfuse_url,
        )
        logger.info(f"Langfuse tracing enabled: {langfuse_url}")
except Exception as e:
    logger.info(f"Langfuse tracing not available: {e}")


def get_langfuse():
    """Return the Langfuse client (or None if not configured)."""
    return _langfuse


def init_llm():
    global _model, _backend

    if GEMINI_API_KEY:
        # Simple API key mode — uses google-genai SDK
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        _model = client
        _backend = "genai"
        logger.info(f"Gemini initialized via API key, model={GEMINI_MODEL}")
    elif GCP_PROJECT:
        # Vertex AI mode — requires service account or gcloud auth
        import vertexai
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        _model = GenerativeModel(GEMINI_MODEL)
        _backend = "vertexai"
        logger.info(f"Vertex AI initialized: project={GCP_PROJECT}, model={GEMINI_MODEL}")
    else:
        raise RuntimeError("Set GEMINI_API_KEY or GCP_PROJECT to enable LLM")


def get_model():
    global _model
    if _model is None:
        init_llm()
    return _model


def shutdown_llm():
    """Shut down the thread pool executor and flush Langfuse. Called during app shutdown."""
    _executor.shutdown(wait=False)
    if _langfuse:
        try:
            _langfuse.flush()
        except Exception:
            pass
    logger.info("LLM executor shut down")


def _sync_generate(model, prompt, system, temperature, json_mode):
    """Run the LLM call synchronously in thread pool."""
    if _backend == "genai":
        from google.genai import types
        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": 8192,
        }
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(
            system_instruction=system if system else None,
            **config_kwargs,
        )
        response = model.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        return response.text
    else:
        # Vertex AI
        from vertexai.generative_models import GenerationConfig
        config_kwargs = {"temperature": temperature, "max_output_tokens": 8192}
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        config = GenerationConfig(**config_kwargs)

        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"System instructions:\n{system}\n\n{prompt}"}]})
        else:
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        response = model.generate_content(contents, generation_config=config)
        return response.text


async def generate(
    prompt: str,
    system: str = "",
    temperature: float = 0.7,
    json_mode: bool = False,
    *,
    parent: Any = None,
    generation_name: str = "gemini-generate",
) -> str:
    """Generate text from Gemini. Returns raw text response.

    Args:
        parent: Optional Langfuse trace or span to nest the generation under.
                If None, creates a standalone trace (backwards-compatible).
        generation_name: Name for the Langfuse generation (e.g. "generate-question").
    """
    model = get_model()

    # Langfuse generation — attach to parent if provided, else standalone trace
    generation = None
    if _langfuse:
        try:
            obs = parent
            if obs is None:
                obs = _langfuse.trace(name="sentinel-llm", metadata={"model": GEMINI_MODEL})
            generation = obs.generation(
                name=generation_name,
                model=GEMINI_MODEL,
                input=prompt[:500],
                model_parameters={"temperature": temperature, "json_mode": json_mode},
            )
        except Exception:
            pass

    t0 = time.time()
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _sync_generate, model, prompt, system, temperature, json_mode),
            timeout=LLM_TIMEOUT,
        )
        if generation:
            try:
                generation.end(output=result[:500], metadata={"duration_s": round(time.time() - t0, 2)})
            except Exception:
                pass
        return result
    except asyncio.TimeoutError:
        logger.error(f"Gemini generation timed out after {LLM_TIMEOUT}s")
        if generation:
            try:
                generation.end(level="ERROR", status_message="timeout")
            except Exception:
                pass
        raise TimeoutError(f"LLM call timed out after {LLM_TIMEOUT}s")
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        if generation:
            try:
                generation.end(level="ERROR", status_message=str(e))
            except Exception:
                pass
        raise


async def generate_json(
    prompt: str,
    system: str = "",
    temperature: float = 0.4,
    *,
    parent: Any = None,
    generation_name: str = "gemini-generate-json",
) -> dict:
    """Generate and parse JSON from Gemini."""
    text = await generate(
        prompt, system=system, temperature=temperature, json_mode=True,
        parent=parent, generation_name=generation_name,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            return json.loads(match.group(1))
        raise
