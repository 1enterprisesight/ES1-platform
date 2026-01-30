# CrewAI Studio

CrewAI Studio is a visual interface for building and managing CrewAI agents and crews. It provides a no-code/low-code experience for creating AI agent workflows.

## Overview

This container builds from the [strnad/CrewAI-Studio](https://github.com/strnad/CrewAI-Studio) open source project. We build from source to support air-gapped deployments.

## Features

- Visual agent definition
- Crew composition and task assignment
- Integration with Ollama for local LLM inference
- Redis-backed state management
- Export crews to Python code

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OPENAI_API_KEY` | - | Optional: OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Optional: Anthropic API key |

### Volume Mounts

| Path | Purpose |
|------|---------|
| `/app/data` | Persistent storage for crew definitions |

## Usage

### Docker Compose

```bash
# Start with other services
docker compose -f docker-compose.yml \
  -f docker-compose.agents.yml \
  -f docker-compose.crewai-studio.yml up -d

# Access at http://localhost:8501
```

### Standalone

```bash
docker build -t crewai-studio .
docker run -p 8501:8501 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  crewai-studio
```

## Integration with ES1 Platform

The Platform Manager UI links to CrewAI Studio from the Agents > Frameworks page. The studio runs as a separate service that can connect to:

- **Ollama**: Local LLM inference
- **Redis**: Shared state and caching
- **CrewAI API**: Runtime execution (port 8100)

## Updating

To update to a newer version of CrewAI Studio:

1. Update the Dockerfile (optionally pin to a specific commit)
2. Rebuild the image:
   ```bash
   docker compose -f docker-compose.crewai-studio.yml build --no-cache
   ```
3. Restart the service:
   ```bash
   docker compose -f docker-compose.crewai-studio.yml up -d
   ```

## Troubleshooting

### Studio won't start

Check if Redis is available:
```bash
docker compose exec redis redis-cli ping
```

### Can't connect to Ollama

Ensure Ollama is running and accessible:
```bash
curl http://localhost:11434/api/tags
```

### Models not showing

Pull models in Ollama first:
```bash
docker compose exec ollama ollama pull llama3.2
```
