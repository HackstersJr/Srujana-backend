#!/usr/bin/env bash
# Docker deployment script for CareCloud AI Agent

set -e

echo "🚀 Deploying CareCloud AI Agent with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before running again."
    echo "   Especially set your OPENAI_API_KEY and database password."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/input data/output logs sql nginx

# Create init.sql if it doesn't exist
if [ ! -f sql/init.sql ]; then
    echo "📝 Creating database initialization script..."
    cat > sql/init.sql << 'EOF'
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
EOF
fi

# Create nginx configuration if it doesn't exist
if [ ! -f nginx/nginx.conf ]; then
    echo "📝 Creating nginx configuration..."
    mkdir -p nginx
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream agent_backend {
        server agent:8000;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://agent_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://agent_backend/health;
            access_log off;
        }
    }
}
EOF
fi

# Function to check if .env has required variables
check_env_vars() {
    if ! grep -q "OPENAI_API_KEY=.*[^[:space:]]" .env; then
        echo "⚠️  Warning: OPENAI_API_KEY is not set in .env file"
        return 1
    fi
    return 0
}

# Check environment variables
if ! check_env_vars; then
    echo "❌ Please set required environment variables in .env file"
    exit 1
fi

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose build --no-cache

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps

# Test the API
echo "🧪 Testing the API..."
sleep 5
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is responding!"
else
    echo "❌ API is not responding. Check logs with: docker-compose logs agent"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Services available:"
echo "  🤖 Agent API: http://localhost:8000"
echo "  📊 API Docs: http://localhost:8000/docs"
echo "  🗄️  Database: localhost:5432"
echo "  🌐 Nginx: http://localhost:80"
echo ""
echo "Useful commands:"
echo "  📋 View logs: docker-compose logs -f"
echo "  🔄 Restart: docker-compose restart"
echo "  🛑 Stop: docker-compose down"
echo "  🗑️  Clean up: docker-compose down -v --rmi all"
echo ""
echo "To access pgAdmin (if enabled): http://localhost:5050"
echo "  Email: admin@carecloud.com"
echo "  Password: admin123"
EOF
