/**
 * Runtime configuration types for ES1 Platform Manager UI
 *
 * This configuration is injected at container startup via window.__ES1_CONFIG__
 * allowing the same Docker image to be deployed across different environments.
 */

export interface RuntimeConfig {
  /**
   * External service URLs - these are opened in the browser
   * They should be accessible from the user's browser, not just internally
   */
  services: {
    /** Grafana monitoring dashboards */
    grafana: string;
    /** Prometheus metrics UI */
    prometheus: string;
    /** Langflow visual LLM flow builder */
    langflow: string;
    /** MLflow model registry and tracking UI */
    mlflow: string;
    /** n8n workflow automation UI */
    n8n: string;
    /** Airflow DAG orchestration UI */
    airflow: string;
    /** CrewAI API documentation (Swagger) */
    crewai: string;
    /** CrewAI Studio visual builder */
    crewaiStudio: string;
    /** AutoGen API documentation (Swagger) */
    autogen: string;
    /** Langfuse LLM observability UI */
    langfuse: string;
    /** Ollama Web UI (Open WebUI) */
    openWebUI: string;
  };

  /**
   * Internal API endpoints - proxied through nginx
   * These paths are relative to the UI origin
   */
  api: {
    /** Platform Manager API base path */
    platform: string;
    /** Agent Router API base path */
    agentRouter: string;
  };

  /**
   * Feature flags for conditional UI elements
   */
  features: {
    /** Enable n8n integration in Automation module */
    enableN8n: boolean;
    /** Enable Langflow integration in AI module */
    enableLangflow: boolean;
    /** Enable CrewAI Studio link in Agents module */
    enableCrewaiStudio: boolean;
    /** Enable Langfuse integration in Observability module */
    enableLangfuse: boolean;
    /** Enable MLflow integration in Models module */
    enableMlflow: boolean;
  };
}

/**
 * Declare the global window property for runtime config injection
 */
declare global {
  interface Window {
    __ES1_CONFIG__?: Partial<RuntimeConfig>;
  }
}
