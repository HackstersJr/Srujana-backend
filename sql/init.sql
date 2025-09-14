-- CareCloud Database Initialization Script

-- Create database if not exists
SELECT 'CREATE DATABASE carecloud'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'carecloud');

-- Connect to carecloud database
\c carecloud;

-- Create tables for agent data
CREATE TABLE IF NOT EXISTS agent_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_queries (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES agent_sessions(session_id),
    query_text TEXT NOT NULL,
    response_text TEXT,
    processing_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agent_sessions_session_id ON agent_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_queries_session_id ON agent_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
