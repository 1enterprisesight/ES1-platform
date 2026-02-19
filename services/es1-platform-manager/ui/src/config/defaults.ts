import type { RuntimeConfig } from './types';

/**
 * Default configuration values for local development
 *
 * These values are used when:
 * 1. Running locally with `npm run dev`
 * 2. No runtime config is injected (fallback)
 *
 * In production/Kubernetes, these are overridden by window.__PLATFORM_CONFIG__
 * which is generated at container startup by docker-entrypoint.sh
 */
export const defaultConfig: RuntimeConfig = {
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
    // These paths are proxied by nginx (production) or vite (development)
    platform: '/api/v1',
    agentRouter: '/agent-router',
  },

  credentials: {
    n8n: {
      email: 'admin@engine.local',
      password: 'Engineadmin!',
    },
    langfuse: {
      email: 'admin@engine.local',
      password: 'Engineadmin!',
    },
  },

  monitoring: {
    grafanaDashboardPrefix: 'platform',
  },

  features: {
    enableN8n: true,
    enableLangflow: true,
    enableCrewaiStudio: true,
    enableAutogenStudio: true,
    enableLangfuse: true,
    enableMlflow: true,
    enableOllama: true,
    enableOpenWebUI: true,
    enableMonitoring: true,
    enableAgentRouter: true,
    enableAirflow: true,
  },
};
