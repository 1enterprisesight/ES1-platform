#!/bin/sh
# docker-entrypoint.sh - Generate KrakenD config from template with env var substitution
#
# Environment variables for backend host overrides:
#   KRAKEND_BACKEND_PLATFORM_API   - Platform Manager API host (default: es1-platform-manager-api:8000)
#   KRAKEND_BACKEND_AIRFLOW        - Airflow webserver host (default: airflow-webserver:8080)
#   KRAKEND_BACKEND_LANGFLOW       - Langflow host (default: langflow:7860)
#   KRAKEND_BACKEND_LANGFUSE       - Langfuse host (default: langfuse:3000)
#   KRAKEND_BACKEND_OLLAMA         - Ollama host (default: ollama:11434)
#   KRAKEND_BACKEND_MLFLOW         - MLflow host (default: mlflow:5000)
#   KRAKEND_BACKEND_N8N            - n8n host (default: n8n:5678)
#   KRAKEND_GATEWAY_NAME           - Gateway display name (default: Platform API Gateway)

set -e

# =============================================================================
# Default values for backend hosts
# =============================================================================
export KRAKEND_BACKEND_PLATFORM_API="${KRAKEND_BACKEND_PLATFORM_API:-es1-platform-manager-api:8000}"
export KRAKEND_BACKEND_AIRFLOW="${KRAKEND_BACKEND_AIRFLOW:-airflow-webserver:8080}"
export KRAKEND_BACKEND_LANGFLOW="${KRAKEND_BACKEND_LANGFLOW:-langflow:7860}"
export KRAKEND_BACKEND_LANGFUSE="${KRAKEND_BACKEND_LANGFUSE:-langfuse:3000}"
export KRAKEND_BACKEND_OLLAMA="${KRAKEND_BACKEND_OLLAMA:-ollama:11434}"
export KRAKEND_BACKEND_MLFLOW="${KRAKEND_BACKEND_MLFLOW:-mlflow:5000}"
export KRAKEND_BACKEND_N8N="${KRAKEND_BACKEND_N8N:-n8n:5678}"
export KRAKEND_GATEWAY_NAME="${KRAKEND_GATEWAY_NAME:-Platform API Gateway}"

# =============================================================================
# Generate krakend.json from template
# =============================================================================
TEMPLATE="/etc/krakend/krakend.json.tmpl"
OUTPUT="/etc/krakend/krakend.json"

if [ -f "$TEMPLATE" ]; then
    echo "Generating KrakenD config from template..."
    envsubst < "$TEMPLATE" > "$OUTPUT"
    echo "KrakenD config generated at $OUTPUT"
else
    echo "No template found at $TEMPLATE, using existing config"
fi

# =============================================================================
# Execute KrakenD
# =============================================================================
exec /usr/bin/krakend "$@"
