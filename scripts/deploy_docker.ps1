# Docker deployment script for CareCloud AI Agent (PowerShell)

Write-Host "🚀 Deploying CareCloud AI Agent with Docker..." -ForegroundColor Green

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is installed
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose is not available. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please edit .env file with your configuration before running again." -ForegroundColor Yellow
    Write-Host "   Especially set your OPENAI_API_KEY and database password." -ForegroundColor Yellow
    exit 1
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Yellow
$directories = @("data\input", "data\output", "logs", "sql", "nginx")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Create init.sql if it doesn't exist
if (-not (Test-Path "sql\init.sql")) {
    Write-Host "📝 Creating database initialization script..." -ForegroundColor Yellow
    @"
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
"@ | Out-File -FilePath "sql\init.sql" -Encoding UTF8
}

# Create nginx configuration if it doesn't exist
if (-not (Test-Path "nginx\nginx.conf")) {
    Write-Host "📝 Creating nginx configuration..." -ForegroundColor Yellow
    @"
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
            proxy_set_header Host `$host;
            proxy_set_header X-Real-IP `$remote_addr;
            proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto `$scheme;
        }

        location /health {
            proxy_pass http://agent_backend/health;
            access_log off;
        }
    }
}
"@ | Out-File -FilePath "nginx\nginx.conf" -Encoding UTF8
}

# Function to check if .env has required variables
function Test-EnvVars {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -notmatch "OPENAI_API_KEY=.+") {
        Write-Host "⚠️  Warning: OPENAI_API_KEY is not set in .env file" -ForegroundColor Yellow
        return $false
    }
    return $true
}

# Check environment variables
if (-not (Test-EnvVars)) {
    Write-Host "❌ Please set required environment variables in .env file" -ForegroundColor Red
    exit 1
}

# Build and start services
Write-Host "🏗️  Building Docker images..." -ForegroundColor Yellow
docker-compose build --no-cache

Write-Host "🚀 Starting services..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services to be ready
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if services are running
Write-Host "🔍 Checking service status..." -ForegroundColor Yellow
docker-compose ps

# Test the API
Write-Host "🧪 Testing the API..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ API is responding!" -ForegroundColor Green
} catch {
    Write-Host "❌ API is not responding. Check logs with: docker-compose logs agent" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Services available:" -ForegroundColor Cyan
Write-Host "  🤖 Agent API: http://localhost:8000" -ForegroundColor White
Write-Host "  📊 API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  🗄️  Database: localhost:5432" -ForegroundColor White
Write-Host "  🌐 Nginx: http://localhost:80" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  📋 View logs: docker-compose logs -f" -ForegroundColor White
Write-Host "  🔄 Restart: docker-compose restart" -ForegroundColor White
Write-Host "  🛑 Stop: docker-compose down" -ForegroundColor White
Write-Host "  🗑️  Clean up: docker-compose down -v --rmi all" -ForegroundColor White
Write-Host ""
Write-Host "To access pgAdmin (if enabled): http://localhost:5050" -ForegroundColor White
Write-Host "  Email: admin@carecloud.com" -ForegroundColor White
Write-Host "  Password: admin123" -ForegroundColor White
