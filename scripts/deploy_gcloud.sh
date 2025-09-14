#!/usr/bin/env bash
# Google Cloud VM Deployment Script for CareCloud AI Agent
# This script deploys the entire agent system to a Google Cloud VM

set -e

echo "🚀 Deploying CareCloud AI Agent to Google Cloud VM..."

# Configuration
PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
VM_NAME="${VM_NAME:-carecloud-agent-vm}"
ZONE="${ZONE:-us-central1-a}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-medium}"
IMAGE_FAMILY="${IMAGE_FAMILY:-ubuntu-2204-lts}"
IMAGE_PROJECT="${IMAGE_PROJECT:-ubuntu-os-cloud}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first:"
        log_error "https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
        log_error "Not authenticated with Google Cloud. Please run: gcloud auth login"
        exit 1
    fi

    # Check if project is set
    if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
        log_error "Please set your PROJECT_ID environment variable or edit this script"
        log_error "Current project: $(gcloud config get-value project 2>/dev/null || echo 'none')"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Create VM instance
create_vm() {
    log_info "Creating Google Cloud VM instance..."

    # Check if VM already exists
    if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" &> /dev/null; then
        log_warning "VM $VM_NAME already exists. Skipping creation..."
        return 0
    fi

    # Create VM with Docker support
    gcloud compute instances create "$VM_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --network-tier=PREMIUM \
        --maintenance-policy=MIGRATE \
        --image-family="$IMAGE_FAMILY" \
        --image-project="$IMAGE_PROJECT" \
        --boot-disk-size=50GB \
        --boot-disk-type=pd-standard \
        --boot-disk-device-name="$VM_NAME" \
        --tags=http-server,https-server \
        --metadata=startup-script="#!/bin/bash
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
curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Create application directory
mkdir -p /home/ubuntu/carecloud-agent
chown ubuntu:ubuntu /home/ubuntu/carecloud-agent

# Install git
apt-get install -y git

echo 'VM setup complete'" \
        --scopes=https://www.googleapis.com/auth/cloud-platform

    log_success "VM instance created successfully"
}

# Copy application files to VM
copy_files() {
    log_info "Copying application files to VM..."

    # Create a temporary tar file
    tar -czf carecloud-agent.tar.gz \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='*.pyc' \
        --exclude='data/embedchain_db' \
        --exclude='logs' \
        --exclude='.env' \
        .

    # Copy files to VM
    gcloud compute scp carecloud-agent.tar.gz "$VM_NAME:/home/ubuntu/" \
        --zone="$ZONE" \
        --project="$PROJECT_ID"

    # Clean up
    rm carecloud-agent.tar.gz

    log_success "Application files copied to VM"
}

# Setup application on VM
setup_application() {
    log_info "Setting up application on VM..."

    # SSH into VM and run setup commands
    gcloud compute ssh "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --command="
set -e

echo 'Setting up CareCloud Agent...'

# Extract application files
cd /home/ubuntu
tar -xzf carecloud-agent.tar.gz -C carecloud-agent/
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
chmod +x scripts/*.sh

echo 'Application setup complete'
"

    log_success "Application setup completed on VM"
}

# Start the application
start_application() {
    log_info "Starting the application..."

    gcloud compute ssh "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --command="
cd /home/ubuntu/carecloud-agent

echo 'Starting CareCloud Agent with Docker Compose...'
docker-compose up -d

echo 'Waiting for services to be healthy...'
sleep 30

# Check if services are running
docker-compose ps

echo 'Application started successfully!'
echo 'API will be available at: http://$(curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H \"Metadata-Flavor: Google\"):8000'
"

    log_success "Application started successfully"
}

# Get VM external IP
get_vm_ip() {
    log_info "Getting VM external IP..."

    EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

    log_success "VM External IP: $EXTERNAL_IP"
    log_info "API Endpoint: http://$EXTERNAL_IP:8000"
    log_info "Health Check: http://$EXTERNAL_IP:8000/health"
    log_info "API Docs: http://$EXTERNAL_IP:8000/docs"
}

# Main deployment function
main() {
    echo "========================================"
    echo "🚀 CareCloud AI Agent - GCloud Deployment"
    echo "========================================"

    # Set project if not already set
    gcloud config set project "$PROJECT_ID" 2>/dev/null || true

    check_prerequisites
    create_vm
    copy_files
    setup_application
    start_application
    get_vm_ip

    echo ""
    echo "========================================"
    log_success "Deployment completed successfully!"
    echo ""
    log_info "Next steps:"
    echo "1. Update the GEMINI_API_KEY in the .env file on the VM"
    echo "2. Restart the application: docker-compose restart"
    echo "3. Test the API endpoints"
    echo "4. Consider setting up a domain and SSL certificate"
    echo ""
    log_info "Useful commands:"
    echo "• SSH to VM: gcloud compute ssh $VM_NAME --zone=$ZONE"
    echo "• View logs: gcloud compute ssh $VM_NAME --zone=$ZONE --command='cd carecloud-agent && docker-compose logs -f'"
    echo "• Stop app: gcloud compute ssh $VM_NAME --zone=$ZONE --command='cd carecloud-agent && docker-compose down'"
    echo "========================================"
}

# Run main function
main "$@"
