# Public Registry Deployment Script for CareCloud AI Agent
# This script pushes the Docker image to a public container registry

param(
    [string]$Registry = "docker.io",  # docker.io for Docker Hub, gcr.io for GCR, etc.
    [string]$Username = "your-dockerhub-username",  # Your registry username
    [string]$Repository = "carecloud-agent",  # Repository name
    [string]$Tag = "latest"  # Image tag
)

# Configuration
$FullImageName = "$Registry/$Username/$Repository`:$Tag"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host "[$Color] $Message" -ForegroundColor $Color
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

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check if Docker is installed
    try {
        $dockerVersion = docker --version 2>$null
        Write-Info "Docker version: $dockerVersion"
    }
    catch {
        Write-Error "Docker is not installed. Please install Docker first."
        exit 1
    }

    # Check if image tar file exists
    if (!(Test-Path "carecloud-agent-image.tar")) {
        Write-Error "carecloud-agent-image.tar not found in current directory."
        Write-Error "Please ensure the Docker image tar file is present."
        exit 1
    }

    # Check if registry credentials are configured
    if ($Username -eq "your-dockerhub-username") {
        Write-Error "Please set your registry username:"
        Write-Error ".\deploy-registry.ps1 -Username your-actual-username"
        exit 1
    }

    Write-Success "Prerequisites check passed"
}

# Login to registry
function Connect-Registry {
    Write-Info "Logging into container registry..."

    switch ($Registry) {
        "docker.io" {
            Write-Info "Logging into Docker Hub..."
            Write-Host "Please enter your Docker Hub password/token when prompted:"
            docker login -u $Username
        }
        "gcr.io" {
            Write-Info "Logging into Google Container Registry..."
            Write-Host "Please ensure you have authenticated with gcloud:"
            Write-Host "gcloud auth configure-docker"
        }
        "ghcr.io" {
            Write-Info "Logging into GitHub Container Registry..."
            Write-Host "Please enter your GitHub Personal Access Token when prompted:"
            docker login ghcr.io -u $Username
        }
        default {
            Write-Warning "Unknown registry: $Registry"
            Write-Warning "Please ensure you are logged in manually"
        }
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Successfully logged into registry"
    }
    else {
        Write-Error "Failed to login to registry"
        exit 1
    }
}

# Load and tag the image
function Initialize-Image {
    Write-Info "Loading and preparing Docker image..."

    # Load the image from tar file
    Write-Info "Loading image from carecloud-agent-image.tar..."
    docker load -i carecloud-agent-image.tar

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to load image from tar file"
        exit 1
    }

    # Get the loaded image ID
    $loadedImage = docker images --format "{{.Repository}} {{.ID}}" |
                   Select-String "agent-project-agent" |
                   Select-Object -First 1

    if (!$loadedImage) {
        Write-Error "Failed to find loaded image 'agent-project-agent'"
        Write-Info "Available images:"
        docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}"
        exit 1
    }

    # Parse the image ID from the output
    $imageParts = $loadedImage -split '\s+'
    $loadedImageId = $imageParts[1]

    if (!$loadedImageId -or $loadedImageId -eq "") {
        Write-Error "Failed to parse image ID from: $loadedImage"
        exit 1
    }

    Write-Info "Loaded image ID: $loadedImageId"

    # Tag the image for the registry
    Write-Info "Tagging image as $FullImageName..."
    docker tag $loadedImageId $FullImageName

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Image prepared for registry"
    }
    else {
        Write-Error "Failed to tag image"
        exit 1
    }
}

# Push image to registry
function Push-Image {
    Write-Info "Pushing image to registry..."

    Write-Info "Pushing $FullImageName..."
    docker push $FullImageName

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Image successfully pushed to registry"
    }
    else {
        Write-Error "Failed to push image to registry"
        exit 1
    }
}

# Generate deployment instructions
function New-DeploymentInstructions {
    Write-Info "Generating deployment instructions..."

    $instructions = @"
# CareCloud AI Agent - Public Registry Deployment

## Image Information
- **Registry**: $Registry
- **Repository**: $Username/$Repository
- **Tag**: $Tag
- **Full Image Name**: $FullImageName

## Quick Deployment Commands

### Using Docker Compose
```yaml
version: '3.8'
services:
  carecloud-agent:
    image: $FullImageName
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=your_gemini_api_key_here
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
```

### Using Docker Run
```powershell
# Run the agent
docker run -d ``
  --name carecloud-agent ``
  -p 8000:8000 ``
  -e GEMINI_API_KEY=your_gemini_api_key_here ``
  -e DB_HOST=host.docker.internal ``
  -e DB_USER=postgres ``
  -e DB_PASSWORD=postgres123 ``
  -e DB_NAME=carecloud ``
  $FullImageName

# Run PostgreSQL (if not using external DB)
docker run -d ``
  --name postgres ``
  -e POSTGRES_DB=carecloud ``
  -e POSTGRES_USER=postgres ``
  -e POSTGRES_PASSWORD=postgres123 ``
  -p 5432:5432 ``
  postgres:15-alpine

# Run Redis (optional)
docker run -d ``
  --name redis ``
  -p 6379:6379 ``
  redis:7-alpine
```

## API Endpoints
- **Health Check**: GET http://localhost:8000/health
- **AI Query**: POST http://localhost:8000/query
- **API Docs**: GET http://localhost:8000/docs

## Required Environment Variables
- `GEMINI_API_KEY`: Your Google Gemini API key
- `DB_HOST`: Database host (default: localhost)
- `DB_USER`: Database user (default: postgres)
- `DB_PASSWORD`: Database password (default: postgres123)
- `DB_NAME`: Database name (default: carecloud)

## Pulling the Image
```powershell
docker pull $FullImageName
```

---
*Generated on $(Get-Date)*
"@

    $instructions | Out-File -FilePath "deployment-instructions.md" -Encoding UTF8
    Write-Success "Deployment instructions generated: deployment-instructions.md"
}

# Main deployment function
function Start-Deployment {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "🚀 CareCloud AI Agent - Registry Deployment" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    Test-Prerequisites
    Connect-Registry
    Initialize-Image
    Push-Image
    New-DeploymentInstructions

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Success "Deployment to public registry completed!"
    Write-Host ""
    Write-Info "Image is now available at: $FullImageName"
    Write-Info "Deployment instructions: deployment-instructions.md"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "1. Share the deployment instructions with your team" -ForegroundColor White
    Write-Host "2. Anyone can now pull and deploy using: docker pull $FullImageName" -ForegroundColor White
    Write-Host "3. Update your CI/CD pipelines to use this image" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
}

# Show usage if requested
if ($args -contains "--help" -or $args -contains "-h") {
    Write-Host "CareCloud AI Agent - Public Registry Deployment Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\deploy-registry.ps1 -Username your-username -Repository carecloud-agent" -ForegroundColor White
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor White
    Write-Host "  -Registry    Container registry (default: docker.io)" -ForegroundColor White
    Write-Host "  -Username    Your registry username" -ForegroundColor White
    Write-Host "  -Repository  Repository name (default: carecloud-agent)" -ForegroundColor White
    Write-Host "  -Tag         Image tag (default: latest)" -ForegroundColor White
    Write-Host ""
    Write-Host "Supported registries:" -ForegroundColor White
    Write-Host "  - docker.io (Docker Hub)" -ForegroundColor White
    Write-Host "  - gcr.io (Google Container Registry)" -ForegroundColor White
    Write-Host "  - ghcr.io (GitHub Container Registry)" -ForegroundColor White
    Write-Host ""
    exit 0
}

# Run main function
Start-Deployment
