#!/bin/sh
# docker-entrypoint.sh - Generates runtime configuration for Platform Manager UI
#
# This script runs at container startup and:
# 1. Generates /usr/share/nginx/html/config.js from environment variables
# 2. Generates /etc/nginx/conf.d/default.conf from nginx.conf.template
#
# Environment variables (with defaults for Docker Compose):
#
# Branding:
#   PAGE_TITLE            - Browser tab title (default: Platform)
#   PLATFORM_NAME         - Platform display name (default: ES1 Platform)
#   META_DESCRIPTION      - HTML meta description (default: Enterprise AI Platform)
#   FAVICON_URL           - Custom favicon URL (default: empty - uses built-in)
#
# Internal services (proxied through nginx):
#   PLATFORM_API_HOST     - Platform Manager API host (default: es1-platform-manager-api)
#   PLATFORM_API_PORT     - Platform Manager API port (default: 8000)
#   AGENT_ROUTER_HOST     - Agent Router host (default: agent-router)
#   AGENT_ROUTER_PORT     - Agent Router port (default: 8102)
#
# External services (opened in browser):
#   GRAFANA_URL           - Grafana dashboard URL (default: http://localhost:3002)
#   PROMETHEUS_URL        - Prometheus UI URL (default: http://localhost:9090)
#   LANGFLOW_URL          - Langflow UI URL (default: http://localhost:7860)
#   MLFLOW_URL            - MLflow UI URL (default: http://localhost:5050)
#   N8N_URL               - n8n UI URL (default: http://localhost:5678)
#   AIRFLOW_URL           - Airflow UI URL (default: http://localhost:8081)
#   CREWAI_URL            - CrewAI API docs URL (default: http://localhost:8100)
#   CREWAI_STUDIO_URL     - CrewAI Studio URL (default: http://localhost:8501)
#   AUTOGEN_URL           - AutoGen API docs URL (default: http://localhost:8101)
#   LANGFUSE_URL          - Langfuse UI URL (default: http://localhost:3000)
#   OPEN_WEBUI_URL        - Open WebUI URL (default: http://localhost:3010)
#   AUTOGEN_STUDIO_URL    - AutoGen Studio URL (default: http://localhost:8502)
#
# Feature flags:
#   ENABLE_N8N            - Enable n8n integration (default: true)
#   ENABLE_LANGFLOW       - Enable Langflow integration (default: true)
#   ENABLE_CREWAI_STUDIO  - Enable CrewAI Studio link (default: true)
#   ENABLE_LANGFUSE       - Enable Langfuse integration (default: true)
#   ENABLE_MLFLOW         - Enable MLflow integration (default: true)

set -e

# =============================================================================
# Default values for branding
# =============================================================================
PAGE_TITLE="${PAGE_TITLE:-Platform}"
PLATFORM_NAME="${PLATFORM_NAME:-ES1 Platform}"
META_DESCRIPTION="${META_DESCRIPTION:-Enterprise AI Platform}"
FAVICON_URL="${FAVICON_URL:-}"

# =============================================================================
# Default values for internal services
# =============================================================================
export PLATFORM_API_HOST="${PLATFORM_API_HOST:-es1-platform-manager-api}"
export PLATFORM_API_PORT="${PLATFORM_API_PORT:-8000}"
export AGENT_ROUTER_HOST="${AGENT_ROUTER_HOST:-agent-router}"
export AGENT_ROUTER_PORT="${AGENT_ROUTER_PORT:-8102}"

# =============================================================================
# Default values for external services (browser URLs)
# =============================================================================
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3002}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
LANGFLOW_URL="${LANGFLOW_URL:-http://localhost:7860}"
MLFLOW_URL="${MLFLOW_URL:-http://localhost:5050}"
N8N_URL="${N8N_URL:-http://localhost:5678}"
AIRFLOW_URL="${AIRFLOW_URL:-http://localhost:8081}"
CREWAI_URL="${CREWAI_URL:-http://localhost:8100}"
CREWAI_STUDIO_URL="${CREWAI_STUDIO_URL:-http://localhost:8501}"
AUTOGEN_URL="${AUTOGEN_URL:-http://localhost:8101}"
LANGFUSE_URL="${LANGFUSE_URL:-http://localhost:3000}"
OPEN_WEBUI_URL="${OPEN_WEBUI_URL:-http://localhost:3010}"
AUTOGEN_STUDIO_URL="${AUTOGEN_STUDIO_URL:-http://localhost:8502}"

# =============================================================================
# Default values for feature flags
# =============================================================================
ENABLE_N8N="${ENABLE_N8N:-true}"
ENABLE_LANGFLOW="${ENABLE_LANGFLOW:-true}"
ENABLE_CREWAI_STUDIO="${ENABLE_CREWAI_STUDIO:-true}"
ENABLE_AUTOGEN_STUDIO="${ENABLE_AUTOGEN_STUDIO:-true}"
ENABLE_LANGFUSE="${ENABLE_LANGFUSE:-true}"
ENABLE_MLFLOW="${ENABLE_MLFLOW:-true}"

# =============================================================================
# Generate nginx configuration from template
# =============================================================================
echo "Generating nginx configuration..."
envsubst '${PLATFORM_API_HOST} ${PLATFORM_API_PORT} ${AGENT_ROUTER_HOST} ${AGENT_ROUTER_PORT}' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

# =============================================================================
# Update index.html with branding (page title and meta description)
# =============================================================================
INDEX_FILE="/usr/share/nginx/html/index.html"
if [ -f "$INDEX_FILE" ]; then
    sed -i "s|<title>[^<]*</title>|<title>${PAGE_TITLE}</title>|g" "$INDEX_FILE"
    # Add or update meta description
    if grep -q 'name="description"' "$INDEX_FILE"; then
        sed -i "s|<meta name=\"description\" content=\"[^\"]*\"|<meta name=\"description\" content=\"${META_DESCRIPTION}\"|g" "$INDEX_FILE"
    else
        sed -i "s|</head>|    <meta name=\"description\" content=\"${META_DESCRIPTION}\" />\n  </head>|g" "$INDEX_FILE"
    fi
    # Update favicon if custom URL provided
    if [ -n "$FAVICON_URL" ]; then
        sed -i "s|<link rel=\"icon\" [^>]*>|<link rel=\"icon\" href=\"${FAVICON_URL}\" />|g" "$INDEX_FILE"
    fi
fi

# =============================================================================
# Generate frontend runtime configuration
# =============================================================================
echo "Generating frontend runtime configuration..."
cat > /usr/share/nginx/html/config.js << EOF
/**
 * Runtime Configuration for Platform Manager UI
 * Generated by docker-entrypoint.sh at container startup
 *
 * DO NOT EDIT - changes will be overwritten on restart
 * To customize, set environment variables on the container
 */
window.__PLATFORM_CONFIG__ = {
  services: {
    // Monitoring
    grafana: '${GRAFANA_URL}',
    prometheus: '${PROMETHEUS_URL}',

    // AI/ML Tools
    langflow: '${LANGFLOW_URL}',
    mlflow: '${MLFLOW_URL}',
    langfuse: '${LANGFUSE_URL}',
    openWebUI: '${OPEN_WEBUI_URL}',

    // Workflow Automation
    n8n: '${N8N_URL}',
    airflow: '${AIRFLOW_URL}',

    // Agent Frameworks
    crewai: '${CREWAI_URL}',
    crewaiStudio: '${CREWAI_STUDIO_URL}',
    autogen: '${AUTOGEN_URL}',
    autogenStudio: '${AUTOGEN_STUDIO_URL}',
  },

  api: {
    platform: '/api/v1',
    agentRouter: '/agent-router',
  },

  features: {
    enableN8n: ${ENABLE_N8N},
    enableLangflow: ${ENABLE_LANGFLOW},
    enableCrewaiStudio: ${ENABLE_CREWAI_STUDIO},
    enableAutogenStudio: ${ENABLE_AUTOGEN_STUDIO},
    enableLangfuse: ${ENABLE_LANGFUSE},
    enableMlflow: ${ENABLE_MLFLOW},
  },

  branding: {
    pageTitle: '${PAGE_TITLE}',
    platformName: '${PLATFORM_NAME}',
    metaDescription: '${META_DESCRIPTION}',
    faviconUrl: '${FAVICON_URL}',
  },
};
EOF

echo "Configuration generated successfully"
echo "  - nginx config: /etc/nginx/conf.d/default.conf"
echo "  - frontend config: /usr/share/nginx/html/config.js"

# =============================================================================
# Execute the main command (nginx)
# =============================================================================
exec "$@"
