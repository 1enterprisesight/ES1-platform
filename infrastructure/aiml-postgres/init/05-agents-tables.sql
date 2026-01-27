-- Agent tables for conversation history, state management, and orchestration

-- Agent definitions
CREATE TABLE agents.definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL, -- llm, tool, orchestrator, crew
    model VARCHAR(255), -- e.g., ollama/llama2, openai/gpt-4
    system_prompt TEXT,
    tools JSONB DEFAULT '[]', -- List of available tools
    config JSONB DEFAULT '{}', -- Agent-specific configuration
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation sessions
CREATE TABLE agents.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents.definitions(id) ON DELETE SET NULL,
    user_id VARCHAR(255),
    title VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'active' -- active, ended, archived
);

CREATE INDEX idx_sessions_agent ON agents.sessions(agent_id);
CREATE INDEX idx_sessions_user ON agents.sessions(user_id);
CREATE INDEX idx_sessions_status ON agents.sessions(status);

-- Conversation messages
CREATE TABLE agents.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES agents.sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- user, assistant, system, tool
    content TEXT NOT NULL,
    tool_calls JSONB, -- For function calling
    tool_results JSONB, -- Results from tool execution
    tokens_input INTEGER,
    tokens_output INTEGER,
    model VARCHAR(255),
    latency_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON agents.messages(session_id);
CREATE INDEX idx_messages_created ON agents.messages(created_at);

-- Agent memory (long-term facts/context)
CREATE TABLE agents.memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents.definitions(id) ON DELETE CASCADE,
    session_id UUID REFERENCES agents.sessions(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL, -- fact, preference, context, summary
    content TEXT NOT NULL,
    embedding_id UUID, -- Reference to vectors for semantic search
    importance_score FLOAT DEFAULT 0.5, -- For memory prioritization
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_agent ON agents.memory(agent_id);
CREATE INDEX idx_memory_session ON agents.memory(session_id);
CREATE INDEX idx_memory_type ON agents.memory(memory_type);

-- Agent networks (crews, swarms, hierarchies)
CREATE TABLE agents.networks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    network_type VARCHAR(50) NOT NULL, -- crew, swarm, hierarchical, mesh
    orchestrator_agent_id UUID REFERENCES agents.definitions(id),
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Network membership
CREATE TABLE agents.network_members (
    network_id UUID NOT NULL REFERENCES agents.networks(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents.definitions(id) ON DELETE CASCADE,
    role VARCHAR(100), -- Role within the network
    config JSONB DEFAULT '{}', -- Agent-specific network config
    PRIMARY KEY (network_id, agent_id)
);

-- Agent execution history (for debugging and analytics)
CREATE TABLE agents.executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents.definitions(id) ON DELETE SET NULL,
    network_id UUID REFERENCES agents.networks(id) ON DELETE SET NULL,
    session_id UUID REFERENCES agents.sessions(id) ON DELETE SET NULL,
    execution_type VARCHAR(50) NOT NULL, -- single, network, scheduled
    input JSONB,
    output JSONB,
    status VARCHAR(50) NOT NULL, -- running, completed, failed, cancelled
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_tokens INTEGER,
    total_cost DECIMAL(10, 6),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_executions_agent ON agents.executions(agent_id);
CREATE INDEX idx_executions_network ON agents.executions(network_id);
CREATE INDEX idx_executions_status ON agents.executions(status);
CREATE INDEX idx_executions_started ON agents.executions(started_at);
