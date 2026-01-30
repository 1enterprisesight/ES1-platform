-- V002: Audit schema for API visibility
-- All service-to-service communication is logged here
-- Phase 6.0a: API Infrastructure Foundation

CREATE SCHEMA IF NOT EXISTS audit;

-- Grant access
GRANT USAGE ON SCHEMA audit TO es1_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL PRIVILEGES ON TABLES TO es1_user;

-- Every API call logged
CREATE TABLE IF NOT EXISTS audit.api_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(64) NOT NULL,      -- Correlation ID for tracing across services
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Source information
    source_service VARCHAR(100),           -- Which service made the call
    source_ip INET,
    user_id VARCHAR(255),
    api_key_id UUID,

    -- Destination information
    destination_service VARCHAR(100),
    method VARCHAR(10),
    path TEXT,
    query_params JSONB,

    -- Request details (hashed for privacy, not full body)
    request_headers JSONB,
    request_body_hash VARCHAR(64),         -- SHA256 hash
    request_size_bytes INTEGER,

    -- Response details
    response_status INTEGER,
    response_body_hash VARCHAR(64),
    response_size_bytes INTEGER,

    -- Performance metrics
    latency_ms INTEGER,
    backend_latency_ms INTEGER,            -- Time spent in backend service

    -- Security context
    auth_method VARCHAR(50),               -- jwt, api_key, mtls, none
    auth_success BOOLEAN,
    security_flags JSONB,                  -- Rate limited, blocked, suspicious, etc.

    -- Error tracking
    error_code VARCHAR(50),
    error_message TEXT,

    -- Extensible metadata
    metadata JSONB DEFAULT '{}'
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_api_requests_timestamp ON audit.api_requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_requests_source ON audit.api_requests(source_service);
CREATE INDEX IF NOT EXISTS idx_api_requests_dest ON audit.api_requests(destination_service);
CREATE INDEX IF NOT EXISTS idx_api_requests_status ON audit.api_requests(response_status);
CREATE INDEX IF NOT EXISTS idx_api_requests_request_id ON audit.api_requests(request_id);
CREATE INDEX IF NOT EXISTS idx_api_requests_user ON audit.api_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_api_requests_path ON audit.api_requests(path);

-- Composite index for service-to-service queries
CREATE INDEX IF NOT EXISTS idx_api_requests_service_pair ON audit.api_requests(source_service, destination_service);

-- Partial index for errors only (faster error analysis)
CREATE INDEX IF NOT EXISTS idx_api_requests_errors ON audit.api_requests(timestamp, destination_service)
    WHERE response_status >= 400;

-- Service dependency map (aggregated view, updated periodically)
CREATE TABLE IF NOT EXISTS audit.service_dependencies (
    source_service VARCHAR(100) NOT NULL,
    destination_service VARCHAR(100) NOT NULL,
    endpoint_pattern VARCHAR(255) NOT NULL,
    call_count BIGINT DEFAULT 0,
    success_count BIGINT DEFAULT 0,
    error_count BIGINT DEFAULT 0,
    avg_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    p99_latency_ms FLOAT,
    last_seen TIMESTAMPTZ,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (source_service, destination_service, endpoint_pattern)
);

CREATE INDEX IF NOT EXISTS idx_service_deps_source ON audit.service_dependencies(source_service);
CREATE INDEX IF NOT EXISTS idx_service_deps_dest ON audit.service_dependencies(destination_service);

-- Security events (auth failures, rate limits, suspicious activity)
CREATE TABLE IF NOT EXISTS audit.security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,       -- auth_failure, rate_limit, blocked_ip, suspicious_pattern
    severity VARCHAR(20) NOT NULL,         -- info, warning, critical
    source_ip INET,
    source_service VARCHAR(100),
    user_id VARCHAR(255),
    api_key_id UUID,
    request_id VARCHAR(64),                -- Link to api_requests
    endpoint VARCHAR(255),
    details JSONB NOT NULL,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(255),
    resolution_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON audit.security_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON audit.security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON audit.security_events(severity);
CREATE INDEX IF NOT EXISTS idx_security_events_unresolved ON audit.security_events(timestamp) WHERE NOT resolved;

-- API keys for service-to-service authentication
CREATE TABLE IF NOT EXISTS audit.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,         -- SHA256 of the actual key
    key_prefix VARCHAR(8) NOT NULL,        -- First 8 chars for identification
    service_name VARCHAR(100),             -- Which service this key is for
    scopes JSONB DEFAULT '[]',             -- Allowed scopes/permissions
    rate_limit_per_minute INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash ON audit.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON audit.api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_service ON audit.api_keys(service_name);

-- Useful views

-- Recent errors view
CREATE OR REPLACE VIEW audit.recent_errors AS
SELECT
    timestamp,
    source_service,
    destination_service,
    method,
    path,
    response_status,
    error_code,
    error_message,
    latency_ms,
    request_id
FROM audit.api_requests
WHERE response_status >= 400
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Service health summary view
CREATE OR REPLACE VIEW audit.service_health AS
SELECT
    destination_service as service,
    COUNT(*) as total_requests,
    COUNT(*) FILTER (WHERE response_status < 400) as success_count,
    COUNT(*) FILTER (WHERE response_status >= 400) as error_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE response_status < 400) / NULLIF(COUNT(*), 0), 2) as success_rate,
    ROUND(AVG(latency_ms)::numeric, 2) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    MAX(timestamp) as last_request
FROM audit.api_requests
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY destination_service;

-- Comments for documentation
COMMENT ON TABLE audit.api_requests IS 'Complete log of all API requests through KrakenD';
COMMENT ON TABLE audit.service_dependencies IS 'Aggregated service-to-service call patterns';
COMMENT ON TABLE audit.security_events IS 'Security-related events requiring attention';
COMMENT ON TABLE audit.api_keys IS 'API keys for service-to-service authentication';

-- Grant permissions on newly created tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO es1_user;
