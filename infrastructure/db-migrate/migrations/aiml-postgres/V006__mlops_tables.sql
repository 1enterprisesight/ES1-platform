-- V006: MLOps tables for model registry and deployment tracking
-- Complements MLflow with platform-specific metadata

-- Model registry
CREATE TABLE IF NOT EXISTS mlops.models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(100) NOT NULL, -- llm, embedding, classifier, regressor, etc.
    framework VARCHAR(100), -- pytorch, tensorflow, onnx, etc.
    artifact_uri TEXT, -- Path to model artifacts
    mlflow_run_id VARCHAR(255), -- Link to MLflow
    input_schema JSONB, -- Expected input format
    output_schema JSONB, -- Expected output format
    metrics JSONB DEFAULT '{}', -- Performance metrics
    tags JSONB DEFAULT '{}',
    description TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_models_name ON mlops.models(name);
CREATE INDEX IF NOT EXISTS idx_models_type ON mlops.models(model_type);

-- Model deployments
CREATE TABLE IF NOT EXISTS mlops.deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES mlops.models(id) ON DELETE RESTRICT,
    environment VARCHAR(50) NOT NULL, -- dev, staging, production
    endpoint_url TEXT,
    deployment_type VARCHAR(50) NOT NULL, -- ollama, vllm, kserve, seldon, custom
    replicas INTEGER DEFAULT 1,
    resources JSONB DEFAULT '{}', -- CPU, memory, GPU requests
    config JSONB DEFAULT '{}', -- Deployment-specific config
    status VARCHAR(50) DEFAULT 'pending', -- pending, deploying, running, failed, stopped
    health_status VARCHAR(50) DEFAULT 'unknown', -- healthy, unhealthy, unknown
    last_health_check TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deployments_model ON mlops.deployments(model_id);
CREATE INDEX IF NOT EXISTS idx_deployments_env ON mlops.deployments(environment);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON mlops.deployments(status);

-- Inference logs for monitoring and debugging
CREATE TABLE IF NOT EXISTS mlops.inference_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id UUID REFERENCES mlops.deployments(id) ON DELETE SET NULL,
    model_id UUID REFERENCES mlops.models(id) ON DELETE SET NULL,
    request_id VARCHAR(255),
    input_data JSONB,
    output_data JSONB,
    latency_ms INTEGER,
    tokens_input INTEGER,
    tokens_output INTEGER,
    status VARCHAR(50), -- success, error
    error_message TEXT,
    user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Partition by month for efficient querying and cleanup
CREATE INDEX IF NOT EXISTS idx_inference_logs_deployment ON mlops.inference_logs(deployment_id);
CREATE INDEX IF NOT EXISTS idx_inference_logs_created ON mlops.inference_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_inference_logs_status ON mlops.inference_logs(status);

-- Feature store (basic implementation, can use Feast for advanced features)
CREATE TABLE IF NOT EXISTS mlops.feature_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    entity_type VARCHAR(100), -- user, item, transaction, etc.
    features JSONB NOT NULL, -- Feature definitions
    source_type VARCHAR(50), -- batch, stream
    source_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feature values (for simple use cases)
CREATE TABLE IF NOT EXISTS mlops.feature_values (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_group_id UUID NOT NULL REFERENCES mlops.feature_groups(id) ON DELETE CASCADE,
    entity_id VARCHAR(255) NOT NULL, -- Entity identifier
    features JSONB NOT NULL, -- Feature values
    event_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(feature_group_id, entity_id, event_timestamp)
);

CREATE INDEX IF NOT EXISTS idx_feature_values_group ON mlops.feature_values(feature_group_id);
CREATE INDEX IF NOT EXISTS idx_feature_values_entity ON mlops.feature_values(entity_id);
CREATE INDEX IF NOT EXISTS idx_feature_values_timestamp ON mlops.feature_values(event_timestamp);

-- Prompt templates and versioning
CREATE TABLE IF NOT EXISTS mlops.prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    template TEXT NOT NULL,
    variables JSONB DEFAULT '[]', -- Expected variables
    model_hint VARCHAR(255), -- Suggested model to use
    tags JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_prompts_name ON mlops.prompts(name);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON mlops.prompts(is_active);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mlops TO aiml_user;
