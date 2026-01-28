# MLflow with PostgreSQL support for ES1 Platform
FROM ghcr.io/mlflow/mlflow:v2.10.2

# Install PostgreSQL driver
RUN pip install --no-cache-dir psycopg2-binary

# Create directory for artifacts
RUN mkdir -p /mlflow/artifacts

# Default port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1
