from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from app.config import GCP_PROJECT, GCP_LOCATION, GEMINI_MODEL

logger = logging.getLogger(__name__)

LLM_TIMEOUT = 45  # seconds — prevent hung LLM calls from blocking the server

_model: GenerativeModel | None = None
_executor = ThreadPoolExecutor(max_workers=3)


def init_llm():
    global _model
    vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
    _model = GenerativeModel(GEMINI_MODEL)
    logger.info(f"Vertex AI initialized: project={GCP_PROJECT}, model={GEMINI_MODEL}")


def get_model() -> GenerativeModel:
    global _model
    if _model is None:
        init_llm()
    return _model


def shutdown_llm():
    """Shut down the thread pool executor. Called during app shutdown."""
    _executor.shutdown(wait=False)
    logger.info("LLM executor shut down")


def _sync_generate(model, contents, config):
    """Run the LLM call synchronously (used in thread pool to avoid blocking event loop
    when the SDK does synchronous credential refresh)."""
    response = model.generate_content(contents, generation_config=config)
    return response.text


async def generate(prompt: str, system: str = "", temperature: float = 0.7, json_mode: bool = False) -> str:
    """Generate text from Gemini. Returns raw text response."""
    model = get_model()

    config_kwargs = {"temperature": temperature, "max_output_tokens": 8192}
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    config = GenerationConfig(**config_kwargs)

    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": f"System instructions:\n{system}\n\n{prompt}"}]})
    else:
        contents.append({"role": "user", "parts": [{"text": prompt}]})

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _sync_generate, model, contents, config),
            timeout=LLM_TIMEOUT,
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Gemini generation timed out after {LLM_TIMEOUT}s")
        raise TimeoutError(f"LLM call timed out after {LLM_TIMEOUT}s")
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        raise


async def generate_json(prompt: str, system: str = "", temperature: float = 0.4) -> dict:
    """Generate and parse JSON from Gemini."""
    text = await generate(prompt, system=system, temperature=temperature, json_mode=True)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            return json.loads(match.group(1))
        raise
