# CareCloud AI Agent - Google Cloud Deployment Guide

## Overview
This guide will help you deploy the entire CareCloud AI Agent system to a Google Cloud VM using Docker containers.

## Prerequisites

### 1. Google Cloud Account & Setup
- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated
- A GCP project created

### 2. API Keys
- Google Gemini API key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

### 3. Local Environment
- Docker and Docker Compose installed
- Git (for cloning the repository)

## Quick Deployment

### Option 1: Using Bash Script (Linux/Mac)

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Run the deployment script
./scripts/deploy_gcloud.sh
```

### Option 2: Using PowerShell Script (Windows)

```powershell
# Set your project ID and run the script
.\scripts\deploy_gcloud.ps1 -ProjectId "your-gcp-project-id"
```

### Option 3: Manual Deployment

#### Step 1: Create Google Cloud VM

```bash
# Set your project and zone
PROJECT_ID="your-gcp-project-id"
ZONE="us-central1-a"

# Create VM with Docker pre-installed
gcloud compute instances create carecloud-agent-vm \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --tags=http-server,https-server \
  --metadata=startup-script="#!/bin/bash
apt-get update
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
usermod -aG docker ubuntu" \
  --scopes=https://www.googleapis.com/auth/cloud-platform
```

#### Step 2: Copy Application Files

```bash
# From your local machine, copy the application
tar -czf carecloud-agent.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='.git' .
gcloud compute scp carecloud-agent.tar.gz carecloud-agent-vm:/home/ubuntu/ --zone=$ZONE
```

#### Step 3: Setup Application on VM

```bash
# SSH into the VM
gcloud compute ssh carecloud-agent-vm --zone=$ZONE

# Extract and setup application
cd /home/ubuntu
tar -xzf carecloud-agent.tar.gz -C carecloud-agent/
cd carecloud-agent

# Create environment file
cat > .env << 'EOF'
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres123
DB_NAME=carecloud

# Google Gemini API Configuration
GEMINI_API_KEY=your_actual_gemini_api_key_here

# LLM Configuration
LLM_MODEL_NAME=gemini-1.5-flash
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
EOF

# Create directories
mkdir -p data/input data/output logs
```

#### Step 4: Start the Application

```bash
# Start with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs
```

## Configuration

### Environment Variables

The application uses the following environment variables (configured in `.env`):

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (with defaults)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres123
DB_NAME=carecloud
LLM_MODEL_NAME=gemini-1.5-flash
SERVER_PORT=8000
```

### Firewall Rules

The VM is created with HTTP/HTTPS tags. You may need to create firewall rules:

```bash
# Allow HTTP traffic
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --target-tags http-server \
  --description "Allow HTTP traffic"

# Allow HTTPS traffic
gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --target-tags https-server \
  --description "Allow HTTPS traffic"
```

## API Endpoints

Once deployed, your API will be available at:

- **Base URL**: `http://VM_EXTERNAL_IP:8000`
- **Health Check**: `GET /health`
- **API Query**: `POST /query`
  ```json
  {
    "query": "Your question here"
  }
  ```
- **API Documentation**: `GET /docs` (Interactive Swagger UI)

## Monitoring & Management

### View Logs

```bash
# SSH into VM and view logs
gcloud compute ssh carecloud-agent-vm --zone=$ZONE
cd carecloud-agent
docker-compose logs -f agent
```

### Restart Services

```bash
# Restart the agent service
docker-compose restart agent

# Restart all services
docker-compose restart
```

### Update Application

```bash
# Pull latest changes (if using git)
git pull origin main

# Rebuild and restart
docker-compose up -d --build
```

### Backup Data

```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres carecloud > backup.sql

# Backup application data
tar -czf data-backup.tar.gz data/ logs/
```

## Troubleshooting

### Common Issues

1. **VM Creation Fails**
   - Check your GCP quotas and billing
   - Verify project ID and zone

2. **Docker Services Won't Start**
   - Check logs: `docker-compose logs`
   - Verify environment variables in `.env`
   - Ensure ports are not in use

3. **API Returns Errors**
   - Check Gemini API key validity
   - Verify network connectivity
   - Check application logs

4. **Database Connection Issues**
   - Wait for PostgreSQL to fully initialize (can take 30-60 seconds)
   - Check database credentials in `.env`

### Useful Commands

```bash
# SSH into VM
gcloud compute ssh carecloud-agent-vm --zone=$ZONE

# View VM status
gcloud compute instances describe carecloud-agent-vm --zone=$ZONE

# Stop VM
gcloud compute instances stop carecloud-agent-vm --zone=$ZONE

# Delete VM (WARNING: This will delete all data)
gcloud compute instances delete carecloud-agent-vm --zone=$ZONE
```

## Security Considerations

1. **API Keys**: Store Gemini API key securely, never commit to version control
2. **Firewall**: Configure minimal required firewall rules
3. **VM Access**: Use SSH keys instead of passwords
4. **Updates**: Keep Docker images and system packages updated
5. **SSL**: Consider adding SSL certificate for production use

## Cost Optimization

- **VM Size**: Start with `e2-medium` ($30-40/month), scale up as needed
- **Disk**: 50GB boot disk is sufficient for most use cases
- **Auto-shutdown**: Consider setting up auto-shutdown for development environments

## Production Deployment

For production deployments, consider:

1. **Load Balancer**: Use GCP Load Balancer for high availability
2. **SSL Certificate**: Use GCP Managed SSL certificates
3. **Monitoring**: Set up Cloud Monitoring and Logging
4. **Backups**: Implement automated database backups
5. **Scaling**: Use managed instance groups for auto-scaling

---

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify configuration in `.env`
3. Ensure all prerequisites are met
4. Check GCP service status

The application includes comprehensive logging and health checks to help with troubleshooting.
