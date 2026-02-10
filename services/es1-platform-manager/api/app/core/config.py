"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database (ES1-platform defaults for local development)
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "platform_manager"
    POSTGRES_USER: str = "es1_user"
    POSTGRES_PASSWORD: str = "es1_dev_password"

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Platform Manager API"
    PLATFORM_VERSION: str = "1.9.0"

    # CORS - restrict in production; wildcard only safe for local dev
    # Set to specific origins (e.g., ["http://localhost:3001"]) when AUTH_MODE != "none"
    CORS_ORIGINS: list[str] = ["*"]

    # Runtime Mode (auto, docker, kubernetes)
    RUNTIME_MODE: str = "auto"

    # ==========================================================================
    # Authentication
    # ==========================================================================

    # Auth mode: "none" (dev), "api-key" (production), "oidc" (enterprise SSO)
    AUTH_MODE: str = "none"

    # Legacy toggle - still respected if AUTH_MODE is "none"
    AUTH_REQUIRED: bool = False

    # Default admin API key — empty by default. Set via env var or generate-credentials.sh.
    # AUTH_MODE=none (dev default) never checks the key, so empty is safe for local dev.
    DEFAULT_API_KEY: str = ""

    # Prefix for generated API keys (white-label)
    API_KEY_PREFIX: str = "pk"

    # JWT signing secret (for future OIDC/session tokens - must be unique, not reuse API key)
    JWT_SECRET: str = ""

    # ==========================================================================
    # KrakenD Configuration
    # ==========================================================================

    # Direct HTTP access (used in Docker mode and for health checks)
    KRAKEND_URL: str = "http://krakend:8080"
    KRAKEND_HEALTH_URL: str = "http://krakend:8080/__health"
    KRAKEND_METRICS_URL: str = "http://krakend:9091/metrics"

    # Config file path (Docker mode - shared volume)
    KRAKEND_CONFIG_PATH: str = "/shared/krakend/krakend.json"

    # Kubernetes-specific settings
    K8S_NAMESPACE: str = "es1-platform"
    KRAKEND_NAMESPACE: str = "es1-infrastructure"
    KRAKEND_CONFIGMAP_NAME: str = "krakend-config"
    KRAKEND_DEPLOYMENT_NAME: str = "krakend"
    KRAKEND_LABEL_SELECTOR: str = "app=krakend"

    # ConfigMap version retention (number of old versions to keep)
    CONFIGMAP_RETENTION_COUNT: int = 10

    # ==========================================================================
    # Discovery Scheduler
    # ==========================================================================

    DISCOVERY_ENABLED: bool = True
    DISCOVERY_INTERVAL_SECONDS: int = 300  # 5 minutes

    # ==========================================================================
    # Airflow Integration
    # ==========================================================================

    AIRFLOW_ENABLED: bool = True

    # Airflow API for Gateway Manager to call
    AIRFLOW_API_URL: str = "http://airflow-webserver:8080/api/v1"

    # Airflow backend host (for KrakenD to proxy to)
    AIRFLOW_BACKEND_HOST: str = "http://airflow-webserver:8080"

    # Airflow credentials (Docker mode)
    AIRFLOW_USERNAME: str = "airflow"
    AIRFLOW_PASSWORD: str = "airflow"

    # Kubernetes secret for Airflow credentials (K8s mode)
    AIRFLOW_CREDENTIALS_SECRET: str = "airflow-credentials"
    AIRFLOW_CREDENTIALS_NAMESPACE: str = "es1-infrastructure"

    # DAG file management (path to Airflow dags folder)
    AIRFLOW_DAGS_PATH: str = "/shared/airflow/dags"

    # ==========================================================================
    # Langflow Integration
    # ==========================================================================

    LANGFLOW_URL: str = "http://langflow:7860"
    LANGFLOW_API_URL: str = "http://langflow:7860/api/v1"
    LANGFLOW_ENABLED: bool = True

    # ==========================================================================
    # Langfuse Integration (Observability)
    # ==========================================================================

    LANGFUSE_URL: str = "http://langfuse:3000"
    LANGFUSE_API_URL: str = "http://langfuse:3000/api"
    LANGFUSE_ENABLED: bool = True
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    # ==========================================================================
    # n8n Integration (Automation)
    # ==========================================================================

    N8N_URL: str = "http://n8n:5678"
    N8N_API_URL: str = "http://n8n:5678/api/v1"
    N8N_ENABLED: bool = False
    N8N_API_KEY: str = ""  # API key generated from n8n Settings > API

    # ==========================================================================
    # Database API Services (for database connection exposure)
    # ==========================================================================

    # Pattern for database API microservices (used in config generator)
    # {db_type} is replaced with: postgres, mysql, mongodb, redis
    DB_API_HOST_PATTERN: str = "http://db-api-{db_type}:8080"

    # ==========================================================================
    # AI/ML Database (for knowledge management)
    # ==========================================================================

    AIML_POSTGRES_HOST: str = "aiml-postgres"
    AIML_POSTGRES_PORT: int = 5432
    AIML_POSTGRES_DB: str = "aiml"
    AIML_POSTGRES_USER: str = "aiml_user"
    AIML_POSTGRES_PASSWORD: str = "aiml_dev_password"

    # ==========================================================================
    # Ollama (for embeddings and LLM inference)
    # ==========================================================================

    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_ENABLED: bool = True

    # ==========================================================================
    # MLflow (experiment tracking and model registry)
    # ==========================================================================

    MLFLOW_URL: str = "http://mlflow:5000"
    MLFLOW_ENABLED: bool = True

    # ==========================================================================
    # Agent Services
    # ==========================================================================

    CREWAI_URL: str = "http://crewai:8100"
    AUTOGEN_URL: str = "http://autogen:8101"
    AGENT_ROUTER_URL: str = "http://agent-router:8102"
    AGENT_ROUTER_ENABLED: bool = True

    # ==========================================================================
    # Monitoring
    # ==========================================================================

    MONITORING_ENABLED: bool = True

    @property
    def auth_enabled(self) -> bool:
        """Whether authentication is required (derived from AUTH_MODE)."""
        if self.AUTH_MODE in ("api-key", "oidc"):
            return True
        if self.AUTH_REQUIRED:
            return True
        return False

    @property
    def cors_allows_credentials(self) -> bool:
        """Only allow credentials if CORS is not wildcard (security requirement)."""
        return "*" not in self.CORS_ORIGINS

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def aiml_database_url(self) -> str:
        """Construct AI/ML PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.AIML_POSTGRES_USER}:{self.AIML_POSTGRES_PASSWORD}"
            f"@{self.AIML_POSTGRES_HOST}:{self.AIML_POSTGRES_PORT}/{self.AIML_POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
