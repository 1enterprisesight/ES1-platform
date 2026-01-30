-- Reference seed: Template agents from frameworks
-- Pre-populates agent definitions for CrewAI and AutoGen templates

-- CrewAI Research Team Agents
INSERT INTO agents.definitions (name, description, agent_type, config, is_active)
VALUES
    ('Researcher', 'Senior Research Analyst - finds comprehensive and accurate information on given topics', 'llm',
     '{"framework": "crewai", "template": "research_team", "role": "Senior Research Analyst", "capabilities": ["research", "analysis", "information-gathering"]}', true),
    ('Writer', 'Content Writer - transforms research findings into clear, engaging content', 'llm',
     '{"framework": "crewai", "template": "research_team", "role": "Content Writer", "capabilities": ["writing", "content-creation", "documentation"]}', true),
    ('Editor', 'Editor - ensures content is polished, accurate, and well-structured', 'llm',
     '{"framework": "crewai", "template": "research_team", "role": "Editor", "capabilities": ["editing", "review", "quality-assurance"]}', true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config;

-- CrewAI Code Review Team Agents
INSERT INTO agents.definitions (name, description, agent_type, config, is_active)
VALUES
    ('Code Reviewer', 'Code Review Specialist - reviews code for quality, patterns, and best practices', 'llm',
     '{"framework": "crewai", "template": "code_review", "role": "Code Reviewer", "capabilities": ["code-review", "static-analysis", "best-practices"]}', true),
    ('Security Analyst', 'Security Analyst - identifies security vulnerabilities and risks in code', 'llm',
     '{"framework": "crewai", "template": "code_review", "role": "Security Analyst", "capabilities": ["security-analysis", "vulnerability-detection", "risk-assessment"]}', true),
    ('Documentation Writer', 'Documentation Writer - creates clear technical documentation', 'llm',
     '{"framework": "crewai", "template": "code_review", "role": "Documentation Writer", "capabilities": ["documentation", "technical-writing", "api-docs"]}', true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config;

-- CrewAI Customer Support Team Agents
INSERT INTO agents.definitions (name, description, agent_type, config, is_active)
VALUES
    ('Intake Specialist', 'Intake Specialist - handles initial customer inquiries and routing', 'llm',
     '{"framework": "crewai", "template": "customer_support", "role": "Intake Specialist", "capabilities": ["customer-intake", "triage", "routing"]}', true),
    ('Technical Support', 'Technical Support Agent - resolves technical issues and provides solutions', 'llm',
     '{"framework": "crewai", "template": "customer_support", "role": "Technical Support", "capabilities": ["technical-support", "troubleshooting", "problem-solving"]}', true),
    ('Quality Assurance', 'QA Specialist - ensures support quality and customer satisfaction', 'llm',
     '{"framework": "crewai", "template": "customer_support", "role": "Quality Assurance", "capabilities": ["quality-assurance", "feedback-analysis", "process-improvement"]}', true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config;

-- AutoGen Agents
INSERT INTO agents.definitions (name, description, agent_type, config, is_active)
VALUES
    ('Code Assistant', 'AI coding assistant that helps with coding tasks, explains code, debugs issues, and suggests improvements', 'llm',
     '{"framework": "autogen", "template": "code_assistant", "agent_type": "assistant", "capabilities": ["coding", "debugging", "code-explanation", "refactoring"]}', true),
    ('User Proxy', 'User proxy agent that represents human input in conversations', 'llm',
     '{"framework": "autogen", "template": "code_assistant", "agent_type": "user_proxy", "capabilities": ["user-interaction", "task-initiation", "feedback"]}', true),
    ('Proponent', 'Debate agent that argues in favor of topics with strong arguments and evidence', 'llm',
     '{"framework": "autogen", "template": "debate", "agent_type": "assistant", "capabilities": ["argumentation", "persuasion", "evidence-presentation"]}', true),
    ('Opponent', 'Debate agent that argues against topics with counterarguments and challenges', 'llm',
     '{"framework": "autogen", "template": "debate", "agent_type": "assistant", "capabilities": ["counterargument", "critical-analysis", "rebuttal"]}', true),
    ('Moderator', 'Debate moderator that ensures fair discussion, summarizes points, and declares conclusions', 'llm',
     '{"framework": "autogen", "template": "debate", "agent_type": "assistant", "capabilities": ["moderation", "summarization", "decision-making"]}', true),
    ('Ideator', 'Brainstorming agent that generates creative ideas and possibilities', 'llm',
     '{"framework": "autogen", "template": "brainstorm", "agent_type": "assistant", "capabilities": ["ideation", "creativity", "brainstorming"]}', true),
    ('Critic', 'Critical analysis agent that evaluates ideas and identifies potential issues', 'llm',
     '{"framework": "autogen", "template": "brainstorm", "agent_type": "assistant", "capabilities": ["critical-thinking", "evaluation", "risk-analysis"]}', true),
    ('Synthesizer', 'Synthesis agent that combines ideas into cohesive solutions', 'llm',
     '{"framework": "autogen", "template": "brainstorm", "agent_type": "assistant", "capabilities": ["synthesis", "integration", "solution-design"]}', true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config;

-- Create agent networks for the template crews
INSERT INTO agents.networks (name, description, network_type, config, is_active)
VALUES
    ('Research Team', 'CrewAI team for researching topics and writing reports', 'crew',
     '{"framework": "crewai", "template": "research_team", "process": "sequential"}', true),
    ('Code Review Team', 'CrewAI team for reviewing and improving code', 'crew',
     '{"framework": "crewai", "template": "code_review", "process": "sequential"}', true),
    ('Customer Support Team', 'CrewAI team for handling customer inquiries', 'crew',
     '{"framework": "crewai", "template": "customer_support", "process": "sequential"}', true),
    ('Code Assistant Team', 'AutoGen conversation for AI-assisted coding', 'hierarchical',
     '{"framework": "autogen", "template": "code_assistant"}', true),
    ('Debate Team', 'AutoGen multi-agent debate on topics', 'mesh',
     '{"framework": "autogen", "template": "debate", "use_group_chat": true}', true),
    ('Brainstorm Team', 'AutoGen brainstorming session with multiple perspectives', 'mesh',
     '{"framework": "autogen", "template": "brainstorm", "use_group_chat": true}', true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config;
