-- Sample seed data: Demo agent definition
-- This creates a sample agent for development/demo purposes

INSERT INTO agents.definitions (
    name,
    description,
    agent_type,
    model,
    system_prompt,
    tools,
    config,
    is_active
)
VALUES (
    'demo-assistant',
    'A helpful demo assistant for testing the platform',
    'llm',
    'ollama/llama3.2',
    'You are a helpful AI assistant. Be concise and accurate in your responses. When you don''t know something, say so rather than making up information.',
    '["search", "calculator"]',
    '{"temperature": 0.7, "max_tokens": 2048}',
    true
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    model = EXCLUDED.model,
    system_prompt = EXCLUDED.system_prompt;
