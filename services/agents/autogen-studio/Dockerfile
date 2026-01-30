# AutoGen Studio - Visual Interface for AutoGen
# Official Microsoft AutoGen Studio for building and testing multi-agent conversations
#
# This provides a web-based interface for:
# - Building AutoGen agent configurations
# - Testing multi-agent conversations
# - Managing agent skills and tools

FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="AutoGen Studio - Visual Multi-Agent Builder"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install AutoGen Studio
# autogenstudio is the official package from Microsoft
RUN pip install --no-cache-dir autogenstudio

# Create data directory for persistence
RUN mkdir -p /app/data

# Expose AutoGen Studio port
EXPOSE 8502

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8502/ || exit 1

# Run AutoGen Studio
# --host 0.0.0.0 to allow external access
# --port 8502 to avoid conflict with CrewAI Studio (8501)
# --appdir /app/data for persistence
CMD ["autogenstudio", "ui", "--host", "0.0.0.0", "--port", "8502", "--appdir", "/app/data"]
