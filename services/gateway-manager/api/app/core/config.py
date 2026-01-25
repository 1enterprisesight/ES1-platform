"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database (ES1-platform defaults for local development)
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "gateway_manager"
    POSTGRES_USER: str = "es1_user"
    POSTGRES_PASSWORD: str = "es1_dev_password"

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "ES1 Gateway Manager API"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Runtime Mode (auto, docker, kubernetes)
    RUNTIME_MODE: str = "auto"

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
    # Airflow Integration
    # ==========================================================================

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
    # Database API Services (for database connection exposure)
    # ==========================================================================

    # Pattern for database API microservices (used in config generator)
    # {db_type} is replaced with: postgres, mysql, mongodb, redis
    DB_API_HOST_PATTERN: str = "http://db-api-{db_type}:8080"

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
