# Database Migration Runner
# Runs versioned SQL migrations for ES1 Platform databases

FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/1enterprisesight/ES1-platform"
LABEL org.opencontainers.image.description="ES1 Platform Database Migration Runner"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy migration runner code
COPY lib/ ./lib/
COPY migrate.py .

# Copy migrations and seeds
COPY migrations/ ./migrations/
COPY seeds/ ./seeds/

# Default command
ENTRYPOINT ["python", "migrate.py"]
CMD ["--all-databases"]
