# CrewAI Studio - Visual Agent Builder
# Built from strnad/CrewAI-Studio source for air-gapped deployment support
#
# This provides a visual interface for building and managing CrewAI agents
# and crews without writing code.

FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="CrewAI Studio - Visual Agent Builder"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Clone CrewAI Studio source
# Using specific commit for reproducibility (update as needed)
RUN git clone --depth 1 https://github.com/strnad/CrewAI-Studio.git .

# Install Python dependencies
# Note: requirements.txt comes from the cloned repo
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for persistence
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
