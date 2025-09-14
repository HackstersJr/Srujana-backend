# Google Cloud VM Deployment Script for CareCloud AI Agent (PowerShell)
# This script deploys the entire agent system to a Google Cloud VM

param(
    [string]$ProjectId = "your-gcp-project-id",
    [string]$VmName = "carecloud-agent-vm",
    [string]$Zone = "us-central1-a",
    [string]$MachineType = "e2-medium"
)

# Configuration
$ImageFamily = "ubuntu-2204-lts"
$ImageProject = "ubuntu-os-cloud"

Write-Host "🚀 Deploying CareCloud AI Agent to Google Cloud VM..." -ForegroundColor Green

# Check prerequisites
function Test-Prerequisites {
    Write-Host "📋 Checking prerequisites..." -ForegroundColor Blue

    # Check if gcloud is installed
    try {
        gcloud --version | Out-Null
        Write-Host "✅ gcloud CLI is installed" -ForegroundColor Green
    } catch {
        Write-Host "❌ gcloud CLI is not installed. Please install it first:" -ForegroundColor Red
        Write-Host "https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
        exit 1
    }

    # Check if authenticated
    $authCheck = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    if (-not $authCheck) {
        Write-Host "❌ Not authenticated with Google Cloud. Please run: gcloud auth login" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Authenticated with Google Cloud" -ForegroundColor Green

    # Check project
    if ($ProjectId -eq "your-gcp-project-id") {
        Write-Host "❌ Please set your ProjectId parameter or edit this script" -ForegroundColor Red
        $currentProject = gcloud config get-value project 2>$null
        if ($currentProject) {
            Write-Host "Current project: $currentProject" -ForegroundColor Yellow
        }
        exit 1
    }

    # Set project
    gcloud config set project $ProjectId 2>$null
    Write-Host "✅ Project set to: $ProjectId" -ForegroundColor Green
}

# Create VM instance
function New-VMInstance {
    Write-Host "🖥️  Creating Google Cloud VM instance..." -ForegroundColor Blue

    # Check if VM already exists
    $vmExists = gcloud compute instances describe $VmName --zone=$Zone --project=$ProjectId 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "⚠️  VM $VmName already exists. Skipping creation..." -ForegroundColor Yellow
        return
    }

    # Create startup script
    $startupScript = @"
#!/bin/bash
# Startup script to install Docker and prepare the VM
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-`$(uname -s)-`$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Create application directory
mkdir -p /home/ubuntu/carecloud-agent
chown ubuntu:ubuntu /home/ubuntu/carecloud-agent

# Install git and other tools
apt-get install -y git curl wget

echo 'VM setup complete'
"@

    # Create VM
    $startupScriptEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($startupScript))

    gcloud compute instances create $VmName `
        --project=$ProjectId `
        --zone=$Zone `
        --machine-type=$MachineType `
        --network-tier=PREMIUM `
        --maintenance-policy=MIGRATE `
        --image-family=$ImageFamily `
        --image-project=$ImageProject `
        --boot-disk-size=50GB `
        --boot-disk-type=pd-standard `
        --boot-disk-device-name=$VmName `
        --tags=http-server,https-server `
        --metadata=startup-script=$startupScript `
        --scopes=https://www.googleapis.com/auth/cloud-platform

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ VM instance created successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create VM instance" -ForegroundColor Red
        exit 1
    }
}

# Copy application files to VM
function Copy-ApplicationFiles {
    Write-Host "📦 Copying application files to VM..." -ForegroundColor Blue

    # Create tar file (exclude unnecessary files)
    $excludePatterns = @(
        "venv",
        "__pycache__",
        ".git",
        "*.pyc",
        "data/embedchain_db",
        "logs",
        ".env"
    )

    $tarCommand = "tar -czf carecloud-agent.tar.gz"
    foreach ($pattern in $excludePatterns) {
        $tarCommand += " --exclude='$pattern'"
    }
    $tarCommand += " ."

    Invoke-Expression $tarCommand

    # Copy to VM
    gcloud compute scp carecloud-agent.tar.gz "$VmName`:/home/ubuntu/" --zone=$Zone --project=$ProjectId

    # Clean up
    Remove-Item carecloud-agent.tar.gz -Force

    Write-Host "✅ Application files copied to VM" -ForegroundColor Green
}

# Setup application on VM
function Install-Application {
    Write-Host "⚙️  Setting up application on VM..." -ForegroundColor Blue

    $setupCommand = @"
set -e

echo 'Setting up CareCloud Agent...'

# Extract application files
cd /home/ubuntu
tar -xzf carecloud-agent.tar.gz -C carecloud-agent/ --strip-components=1
rm carecloud-agent.tar.gz

cd carecloud-agent

# Create .env file
cat > .env << 'EOF'
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres123
DB_NAME=carecloud

# Google Gemini API Configuration
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE

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

# Data Paths
DATA_DIR=data
INPUT_DIR=data/input
OUTPUT_DIR=data/output

# Logging
LOG_FILE_PATH=logs/agent.log
EOF

echo 'Environment file created. Please update GEMINI_API_KEY with your actual key.'

# Create necessary directories
mkdir -p data/input data/output logs

# Make scripts executable
chmod +x scripts/*.sh 2>/dev/null || true

echo 'Application setup complete'
"@

    gcloud compute ssh $VmName --zone=$Zone --project=$ProjectId --command=$setupCommand

    Write-Host "✅ Application setup completed on VM" -ForegroundColor Green
}

# Start the application
function Start-Application {
    Write-Host "🚀 Starting the application..." -ForegroundColor Blue

    $startCommand = @"
cd /home/ubuntu/carecloud-agent

echo 'Starting CareCloud Agent with Docker Compose...'
docker-compose up -d

echo 'Waiting for services to be healthy...'
sleep 30

# Check if services are running
docker-compose ps

echo 'Application started successfully!'
"@

    gcloud compute ssh $VmName --zone=$Zone --project=$ProjectId --command=$startCommand

    Write-Host "✅ Application started successfully" -ForegroundColor Green
}

# Get VM external IP and show endpoints
function Get-VMEndpoints {
    Write-Host "🌐 Getting VM information..." -ForegroundColor Blue

    $externalIP = gcloud compute instances describe $VmName `
        --zone=$Zone `
        --project=$ProjectId `
        --format="get(networkInterfaces[0].accessConfigs[0].natIP)"

    Write-Host "" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "" -ForegroundColor White
    Write-Host "VM External IP: $externalIP" -ForegroundColor Green
    Write-Host "API Endpoint: http://$externalIP`:8000" -ForegroundColor Green
    Write-Host "Health Check: http://$externalIP`:8000/health" -ForegroundColor Green
    Write-Host "API Docs: http://$externalIP`:8000/docs" -ForegroundColor Green
    Write-Host "" -ForegroundColor White
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Update the GEMINI_API_KEY in the .env file on the VM" -ForegroundColor White
    Write-Host "2. Restart the application: docker-compose restart" -ForegroundColor White
    Write-Host "3. Test the API endpoints" -ForegroundColor White
    Write-Host "4. Consider setting up a domain and SSL certificate" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "• SSH to VM: gcloud compute ssh $VmName --zone=$Zone" -ForegroundColor White
    Write-Host "• View logs: gcloud compute ssh $VmName --zone=$Zone --command='cd carecloud-agent && docker-compose logs -f'" -ForegroundColor White
    Write-Host "• Stop app: gcloud compute ssh $VmName --zone=$Zone --command='cd carecloud-agent && docker-compose down'" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
}

# Main deployment function
function Start-Deployment {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "🚀 CareCloud AI Agent - GCloud Deployment" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan

    Test-Prerequisites
    New-VMInstance
    Copy-ApplicationFiles
    Install-Application
    Start-Application
    Get-VMEndpoints
}

# Run deployment
Start-Deployment
