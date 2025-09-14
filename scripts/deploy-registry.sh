#!/usr/bin/env bash
# Public Registry Deployment Script for CareCloud AI Agent
# This script pushes the Docker image to a public container registry

set -e

echo "🚀 Deploying CareCloud AI Agent to Public Container Registry..."

# Configuration - Update these with your registry details
REGISTRY="${REGISTRY:-docker.io}"  # docker.io for Docker Hub, gcr.io for GCR, etc.
USERNAME="${USERNAME:-your-dockerhub-username}"  # Your registry username
REPOSITORY="${REPOSITORY:-carecloud-agent}"  # Repository name
TAG="${TAG:-latest}"  # Image tag
FULL_IMAGE_NAME="${REGISTRY}/${USERNAME}/${REPOSITORY}:${TAG}"

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

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if image tar file exists
    if [ ! -f "carecloud-agent-image.tar" ]; then
        log_error "carecloud-agent-image.tar not found in current directory."
        log_error "Please ensure the Docker image tar file is present."
        exit 1
    fi

    # Check if registry credentials are configured
    if [ "$USERNAME" = "your-dockerhub-username" ]; then
        log_error "Please set your registry username:"
        log_error "export USERNAME=your-actual-username"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Login to registry
login_to_registry() {
    log_info "Logging into container registry..."

    case $REGISTRY in
        "docker.io")
            log_info "Logging into Docker Hub..."
            echo "Please enter your Docker Hub password/token:"
            docker login -u "$USERNAME"
            ;;
        "gcr.io")
            log_info "Logging into Google Container Registry..."
            echo "Please ensure you have authenticated with gcloud:"
            echo "gcloud auth configure-docker"
            ;;
        "ghcr.io")
            log_info "Logging into GitHub Container Registry..."
            echo "Please enter your GitHub Personal Access Token:"
            docker login ghcr.io -u "$USERNAME"
            ;;
        *)
            log_warning "Unknown registry: $REGISTRY"
            log_warning "Please ensure you are logged in manually"
            ;;
    esac

    if [ $? -eq 0 ]; then
        log_success "Successfully logged into registry"
    else
        log_error "Failed to login to registry"
        exit 1
    fi
}

# Load and tag the image
prepare_image() {
    log_info "Loading and preparing Docker image..."

    # Load the image from tar file
    log_info "Loading image from carecloud-agent-image.tar..."
    docker load -i carecloud-agent-image.tar

    # Get the loaded image ID
    LOADED_IMAGE_ID=$(docker images --format "table {{.Repository}}\t{{.ID}}" | grep "agent-project-agent" | head -n1 | awk '{print $2}')

    if [ -z "$LOADED_IMAGE_ID" ]; then
        log_error "Failed to find loaded image"
        exit 1
    fi

    log_info "Loaded image ID: $LOADED_IMAGE_ID"

    # Tag the image for the registry
    log_info "Tagging image as $FULL_IMAGE_NAME..."
    docker tag "$LOADED_IMAGE_ID" "$FULL_IMAGE_NAME"

    log_success "Image prepared for registry"
}

# Push image to registry
push_image() {
    log_info "Pushing image to registry..."

    log_info "Pushing $FULL_IMAGE_NAME..."
    docker push "$FULL_IMAGE_NAME"

    if [ $? -eq 0 ]; then
        log_success "Image successfully pushed to registry"
    else
        log_error "Failed to push image to registry"
        exit 1
    fi
}

# Generate deployment instructions
generate_deployment_instructions() {
    log_info "Generating deployment instructions..."

    cat << EOF > deployment-instructions.md
# CareCloud AI Agent - Public Registry Deployment

## Image Information
- **Registry**: $REGISTRY
- **Repository**: $USERNAME/$REPOSITORY
- **Tag**: $TAG
- **Full Image Name**: $FULL_IMAGE_NAME

## Quick Deployment Commands

### Using Docker Compose
\`\`\`yaml
version: '3.8'
services:
  carecloud-agent:
    image: $FULL_IMAGE_NAME
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=AIzaSyAWz4pZRDx5OJbFDsQqK1-s8dTjTfXcOig
      - DB_HOST=localhost
      - DB_USER=postgres
      - DB_PASSWORD=postgres123
      - DB_NAME=carecloud
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=carecloud
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres123
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
\`\`\`

### Using Docker Run
\`\`\`bash
# Run the agent
docker run -d \\
  --name carecloud-agent \\
  -p 8000:8000 \\
  -e GEMINI_API_KEY=AIzaSyAWz4pZRDx5OJbFDsQqK1-s8dTjTfXcOig \\
  -e DB_HOST=host.docker.internal \\
  -e DB_USER=postgres \\
  -e DB_PASSWORD=postgres123 \\
  -e DB_NAME=carecloud \\
  $FULL_IMAGE_NAME

# Run PostgreSQL (if not using external DB)
docker run -d \\
  --name postgres \\
  -e POSTGRES_DB=carecloud \\
  -e POSTGRES_USER=postgres \\
  -e POSTGRES_PASSWORD=postgres123 \\
  -p 5432:5432 \\
  postgres:15-alpine

# Run Redis (optional)
docker run -d \\
  --name redis \\
  -p 6379:6379 \\
  redis:7-alpine
\`\`\`

## API Endpoints
- **Health Check**: GET http://localhost:8000/health
- **AI Query**: POST http://localhost:8000/query
- **API Docs**: GET http://localhost:8000/docs

## Required Environment Variables
- \`GEMINI_API_KEY\`: Your Google Gemini API key
- \`DB_HOST\`: Database host (default: localhost)
- \`DB_USER\`: Database user (default: postgres)
- \`DB_PASSWORD\`: Database password (default: postgres123)
- \`DB_NAME\`: Database name (default: carecloud)

## Pulling the Image
\`\`\`bash
docker pull $FULL_IMAGE_NAME
\`\`\`

---
*Generated on $(date)*
EOF

    log_success "Deployment instructions generated: deployment-instructions.md"
}

# Main deployment function
main() {
    echo "========================================"
    echo "🚀 CareCloud AI Agent - Registry Deployment"
    echo "========================================"

    check_prerequisites
    login_to_registry
    prepare_image
    push_image
    generate_deployment_instructions

    echo ""
    echo "========================================"
    log_success "Deployment to public registry completed!"
    echo ""
    log_info "Image is now available at: $FULL_IMAGE_NAME"
    log_info "Deployment instructions: deployment-instructions.md"
    echo ""
    log_info "Next steps:"
    echo "1. Share the deployment instructions with your team"
    echo "2. Anyone can now pull and deploy using: docker pull $FULL_IMAGE_NAME"
    echo "3. Update your CI/CD pipelines to use this image"
    echo "========================================"
}

# Show usage if requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "CareCloud AI Agent - Public Registry Deployment Script"
    echo ""
    echo "Usage:"
    echo "  export REGISTRY=docker.io"
    echo "  export USERNAME=your-username"
    echo "  export REPOSITORY=carecloud-agent"
    echo "  export TAG=latest"
    echo "  ./deploy-registry.sh"
    echo ""
    echo "Supported registries:"
    echo "  - docker.io (Docker Hub)"
    echo "  - gcr.io (Google Container Registry)"
    echo "  - ghcr.io (GitHub Container Registry)"
    echo ""
    exit 0
fi

# Run main function
main "$@"
