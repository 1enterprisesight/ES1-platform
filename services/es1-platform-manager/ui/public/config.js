/**
 * Runtime Configuration for ES1 Platform Manager UI
 *
 * This file is loaded BEFORE the React app and sets window.__ES1_CONFIG__
 *
 * In development (npm run dev):
 *   - This file provides default localhost URLs
 *   - Vite proxies /api and /agent-router to backend services
 *
 * In production (Docker/Kubernetes):
 *   - docker-entrypoint.sh generates this file from environment variables
 *   - nginx proxies /api and /agent-router to backend services
 *   - External URLs point to Ingress or LoadBalancer endpoints
 *
 * To customize for your environment, set these environment variables:
 *   GRAFANA_URL, PROMETHEUS_URL, LANGFLOW_URL, MLFLOW_URL,
 *   N8N_URL, AIRFLOW_URL, CREWAI_URL, CREWAI_STUDIO_URL, etc.
 */
window.__ES1_CONFIG__ = {
  services: {
    // Monitoring
    grafana: 'http://localhost:3002',
    prometheus: 'http://localhost:9090',

    // AI/ML Tools
    langflow: 'http://localhost:7860',
    mlflow: 'http://localhost:5050',
    langfuse: 'http://localhost:3000',
    openWebUI: 'http://localhost:3010',

    // Workflow Automation
    n8n: 'http://localhost:5678',
    airflow: 'http://localhost:8081',

    // Agent Frameworks
    crewai: 'http://localhost:8100',
    crewaiStudio: 'http://localhost:8501',
    autogen: 'http://localhost:8101',
    autogenStudio: 'http://localhost:8502',
  },

  api: {
    platform: '/api/v1',
    agentRouter: '/agent-router',
  },

  features: {
    enableN8n: true,
    enableLangflow: true,
    enableCrewaiStudio: true,
    enableAutogenStudio: true,
    enableLangfuse: true,
    enableMlflow: true,
  },
};
