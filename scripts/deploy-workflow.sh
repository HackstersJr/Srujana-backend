#!/usr/bin/env bash
# CareCloud AI Agent - Complete Registry Deployment Workflow
# This script demonstrates the full workflow from build to registry deployment

set -e

echo "🚀 CareCloud AI Agent - Complete Registry Deployment Workflow"
echo "============================================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

# Configuration
REGISTRY="${REGISTRY:-docker.io}"
USERNAME="${USERNAME:-your-registry-username}"
REPOSITORY="${REPOSITORY:-carecloud-agent}"
TAG="${TAG:-latest}"

# Step 1: Build the Docker image
build_image() {
    log_info "Step 1: Building Docker image..."

    if [ -f "carecloud-agent-image.tar" ]; then
        log_warning "Image tar file already exists. Skipping build."
        log_info "To rebuild, delete carecloud-agent-image.tar first."
        return 0
    fi

    # Build the image
    docker-compose build

    # Save the image
    log_info "Saving image to tar file..."
    docker save agent-project-agent:latest -o carecloud-agent-image.tar

    log_success "Image built and saved successfully"
}

# Step 2: Deploy to registry
deploy_to_registry() {
    log_info "Step 2: Deploying to container registry..."

    # Set environment variables for the registry script
    export REGISTRY USERNAME REPOSITORY TAG

    # Run the registry deployment script
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        powershell.exe -ExecutionPolicy Bypass -File ".\scripts\deploy-registry.ps1"
    else
        # Linux/macOS
        ./scripts/deploy-registry.sh
    fi

    log_success "Image deployed to registry successfully"
}

# Step 3: Test deployment
test_deployment() {
    log_info "Step 3: Testing deployment..."

    FULL_IMAGE_NAME="${REGISTRY}/${USERNAME}/${REPOSITORY}:${TAG}"

    log_info "Testing image pull..."
    docker pull "$FULL_IMAGE_NAME"

    log_info "Testing container run..."
    CONTAINER_ID=$(docker run -d -p 8001:8000 --name test-carecloud-agent "$FULL_IMAGE_NAME")

    # Wait for container to start
    sleep 10

    # Test health endpoint
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        log_success "Health check passed!"
    else
        log_error "Health check failed!"
        docker logs "$CONTAINER_ID"
        docker stop "$CONTAINER_ID"
        docker rm "$CONTAINER_ID"
        exit 1
    fi

    # Clean up test container
    docker stop "$CONTAINER_ID" > /dev/null 2>&1
    docker rm "$CONTAINER_ID" > /dev/null 2>&1

    log_success "Deployment test completed successfully"
}

# Step 4: Show next steps
show_next_steps() {
    log_info "Step 4: Next steps and information"

    FULL_IMAGE_NAME="${REGISTRY}/${USERNAME}/${REPOSITORY}:${TAG}"

    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📦 Image Information:"
    echo "   Registry: $REGISTRY"
    echo "   Repository: $USERNAME/$REPOSITORY"
    echo "   Tag: $TAG"
    echo "   Full Image: $FULL_IMAGE_NAME"
    echo ""
    echo "🚀 Deployment Commands:"
    echo "   # Pull the image"
    echo "   docker pull $FULL_IMAGE_NAME"
    echo ""
    echo "   # Run with Docker Compose"
    echo "   docker-compose up -d"
    echo ""
    echo "   # Or run directly"
    echo "   docker run -d -p 8000:8000 -e GEMINI_API_KEY=your_key_here $FULL_IMAGE_NAME"
    echo ""
    echo "📚 Documentation:"
    echo "   - Deployment Guide: REGISTRY_DEPLOYMENT_README.md"
    echo "   - Generated Instructions: deployment-instructions.md"
    echo "   - API Documentation: http://localhost:8000/docs (when running)"
    echo ""
    echo "🔧 Environment Variables Needed:"
    echo "   - GEMINI_API_KEY: Your Google Gemini API key"
    echo "   - DB_HOST: Database host (default: localhost)"
    echo "   - DB_USER: Database user (default: postgres)"
    echo "   - DB_PASSWORD: Database password (default: postgres123)"
    echo "   - DB_NAME: Database name (default: carecloud)"
    echo ""
    echo "📞 Support:"
    echo "   - Check logs: docker logs <container-name>"
    echo "   - Health check: curl http://localhost:8000/health"
    echo "   - API docs: http://localhost:8000/docs"
}

# Main workflow
main() {
    echo "This script will:"
    echo "1. Build the Docker image (if not already built)"
    echo "2. Deploy to container registry"
    echo "3. Test the deployment"
    echo "4. Show deployment information and next steps"
    echo ""

    # Check if username is set
    if [ "$USERNAME" = "your-registry-username" ]; then
        log_error "Please set your registry username:"
        echo "export USERNAME=your-actual-username"
        echo ""
        echo "Or run with:"
        echo "USERNAME=your-username ./scripts/deploy-workflow.sh"
        exit 1
    fi

    # Confirm before proceeding
    read -p "Continue with deployment to $REGISTRY as $USERNAME? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled."
        exit 0
    fi

    # Run workflow steps
    build_image
    deploy_to_registry
    test_deployment
    show_next_steps
}

# Show usage
show_usage() {
    echo "CareCloud AI Agent - Complete Registry Deployment Workflow"
    echo ""
    echo "Usage:"
    echo "  export USERNAME=your-registry-username"
    echo "  export REGISTRY=docker.io  # optional, defaults to docker.io"
    echo "  export REPOSITORY=carecloud-agent  # optional"
    echo "  export TAG=latest  # optional"
    echo "  ./scripts/deploy-workflow.sh"
    echo ""
    echo "Supported registries:"
    echo "  - docker.io (Docker Hub)"
    echo "  - gcr.io (Google Container Registry)"
    echo "  - ghcr.io (GitHub Container Registry)"
    echo ""
    echo "Examples:"
    echo "  # Docker Hub"
    echo "  USERNAME=myuser ./scripts/deploy-workflow.sh"
    echo ""
    echo "  # Google Container Registry"
    echo "  REGISTRY=gcr.io USERNAME=my-gcp-project ./scripts/deploy-workflow.sh"
    echo ""
    echo "  # GitHub Container Registry"
    echo "  REGISTRY=ghcr.io USERNAME=my-github-user ./scripts/deploy-workflow.sh"
}

# Handle command line arguments
case "$1" in
    --help|-h)
        show_usage
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
