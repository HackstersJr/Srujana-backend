# CareCloud AI Agent - Complete Registry Deployment Workflow
# This script demonstrates the full workflow from build to registry deployment

param(
    [string]$Registry = "docker.io",
    [string]$Username = "your-registry-username",
    [string]$Repository = "carecloud-agent",
    [string]$Tag = "latest"
)

# Colors for output
$Green = "Green"
$Blue = "Cyan"
$Yellow = "Yellow"
$Red = "Red"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" $Blue
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" $Green
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "[WARNING] $Message" $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" $Red
}

# Step 1: Build the Docker image
function New-DockerImage {
    Write-Info "Step 1: Building Docker image..."

    if (Test-Path "carecloud-agent-image.tar") {
        Write-Warning "Image tar file already exists. Skipping build."
        Write-Info "To rebuild, delete carecloud-agent-image.tar first."
        return
    }

    # Build the image
    docker-compose build

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build Docker image"
        exit 1
    }

    # Save the image
    Write-Info "Saving image to tar file..."
    docker save agent-project-agent:latest -o carecloud-agent-image.tar

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Image built and saved successfully"
    }
    else {
        Write-Error "Failed to save Docker image"
        exit 1
    }
}

# Step 2: Deploy to registry
function Publish-ToRegistry {
    Write-Info "Step 2: Deploying to container registry..."

    # Run the registry deployment script
    $env:REGISTRY = $Registry
    $env:USERNAME = $Username
    $env:REPOSITORY = $Repository
    $env:TAG = $Tag

    & ".\scripts\deploy-registry.ps1" -Registry $Registry -Username $Username -Repository $Repository -Tag $Tag

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Image deployed to registry successfully"
    }
    else {
        Write-Error "Failed to deploy to registry"
        exit 1
    }
}

# Step 3: Test deployment
function Test-Deployment {
    Write-Info "Step 3: Testing deployment..."

    $FullImageName = "$Registry/$Username/$Repository`:$Tag"

    Write-Info "Testing image pull..."
    docker pull $FullImageName

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to pull image from registry"
        exit 1
    }

    Write-Info "Testing container run..."
    $containerId = docker run -d -p 8001:8000 --name test-carecloud-agent $FullImageName

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start test container"
        exit 1
    }

    # Wait for container to start
    Start-Sleep -Seconds 10

    # Test health endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Success "Health check passed!"
        }
        else {
            Write-Error "Health check failed with status: $($response.StatusCode)"
            docker logs $containerId
            throw "Health check failed"
        }
    }
    catch {
        Write-Error "Health check failed!"
        docker logs $containerId
        docker stop $containerId 2>$null | Out-Null
        docker rm $containerId 2>$null | Out-Null
        exit 1
    }

    # Clean up test container
    docker stop $containerId 2>$null | Out-Null
    docker rm $containerId 2>$null | Out-Null

    Write-Success "Deployment test completed successfully"
}

# Step 4: Show next steps
function Show-NextSteps {
    Write-Info "Step 4: Next steps and information"

    $FullImageName = "$Registry/$Username/$Repository`:$Tag"

    Write-Host ""
    Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 Image Information:" -ForegroundColor Cyan
    Write-Host "   Registry: $Registry" -ForegroundColor White
    Write-Host "   Repository: $Username/$Repository" -ForegroundColor White
    Write-Host "   Tag: $Tag" -ForegroundColor White
    Write-Host "   Full Image: $FullImageName" -ForegroundColor White
    Write-Host ""
    Write-Host "🚀 Deployment Commands:" -ForegroundColor Cyan
    Write-Host "   # Pull the image" -ForegroundColor White
    Write-Host "   docker pull $FullImageName" -ForegroundColor White
    Write-Host ""
    Write-Host "   # Run with Docker Compose" -ForegroundColor White
    Write-Host "   docker-compose up -d" -ForegroundColor White
    Write-Host ""
    Write-Host "   # Or run directly" -ForegroundColor White
    Write-Host "   docker run -d -p 8000:8000 -e GEMINI_API_KEY=your_key_here $FullImageName" -ForegroundColor White
    Write-Host ""
    Write-Host "📚 Documentation:" -ForegroundColor Cyan
    Write-Host "   - Deployment Guide: REGISTRY_DEPLOYMENT_README.md" -ForegroundColor White
    Write-Host "   - Generated Instructions: deployment-instructions.md" -ForegroundColor White
    Write-Host "   - API Documentation: http://localhost:8000/docs (when running)" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Environment Variables Needed:" -ForegroundColor Cyan
    Write-Host "   - GEMINI_API_KEY: Your Google Gemini API key" -ForegroundColor White
    Write-Host "   - DB_HOST: Database host (default: localhost)" -ForegroundColor White
    Write-Host "   - DB_USER: Database user (default: postgres)" -ForegroundColor White
    Write-Host "   - DB_PASSWORD: Database password (default: postgres123)" -ForegroundColor White
    Write-Host "   - DB_NAME: Database name (default: carecloud)" -ForegroundColor White
    Write-Host ""
    Write-Host "📞 Support:" -ForegroundColor Cyan
    Write-Host "   - Check logs: docker logs <container-name>" -ForegroundColor White
    Write-Host "   - Health check: curl http://localhost:8000/health" -ForegroundColor White
    Write-Host "   - API docs: http://localhost:8000/docs" -ForegroundColor White
}

# Main workflow
function Start-DeploymentWorkflow {
    Write-Host "🚀 CareCloud AI Agent - Complete Registry Deployment Workflow" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This script will:" -ForegroundColor White
    Write-Host "1. Build the Docker image (if not already built)" -ForegroundColor White
    Write-Host "2. Deploy to container registry" -ForegroundColor White
    Write-Host "3. Test the deployment" -ForegroundColor White
    Write-Host "4. Show deployment information and next steps" -ForegroundColor White
    Write-Host ""

    # Check if username is set
    if ($Username -eq "your-registry-username") {
        Write-Error "Please set your registry username:"
        Write-Host ".\scripts\deploy-workflow.ps1 -Username your-actual-username" -ForegroundColor White
        Write-Host ""
        exit 1
    }

    # Confirm before proceeding
    $confirmation = Read-Host "Continue with deployment to $Registry as $Username? (y/N)"
    if ($confirmation -notmatch "^[Yy]$") {
        Write-Info "Deployment cancelled."
        exit 0
    }

    # Run workflow steps
    New-DockerImage
    Publish-ToRegistry
    Test-Deployment
    Show-NextSteps
}

# Show usage
function Show-Usage {
    Write-Host "CareCloud AI Agent - Complete Registry Deployment Workflow" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\scripts\deploy-workflow.ps1 -Username your-registry-username [-Registry docker.io] [-Repository carecloud-agent] [-Tag latest]" -ForegroundColor White
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor White
    Write-Host "  -Registry    Container registry (default: docker.io)" -ForegroundColor White
    Write-Host "  -Username    Your registry username (required)" -ForegroundColor White
    Write-Host "  -Repository  Repository name (default: carecloud-agent)" -ForegroundColor White
    Write-Host "  -Tag         Image tag (default: latest)" -ForegroundColor White
    Write-Host ""
    Write-Host "Supported registries:" -ForegroundColor White
    Write-Host "  - docker.io (Docker Hub)" -ForegroundColor White
    Write-Host "  - gcr.io (Google Container Registry)" -ForegroundColor White
    Write-Host "  - ghcr.io (GitHub Container Registry)" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  # Docker Hub" -ForegroundColor White
    Write-Host "  .\scripts\deploy-workflow.ps1 -Username myuser" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Google Container Registry" -ForegroundColor White
    Write-Host "  .\scripts\deploy-workflow.ps1 -Registry gcr.io -Username my-gcp-project" -ForegroundColor White
    Write-Host ""
    Write-Host "  # GitHub Container Registry" -ForegroundColor White
    Write-Host "  .\scripts\deploy-workflow.ps1 -Registry ghcr.io -Username my-github-user" -ForegroundColor White
}

# Handle command line arguments
if ($args -contains "--help" -or $args -contains "-h") {
    Show-Usage
    exit 0
}

# Run main workflow
Start-DeploymentWorkflow
