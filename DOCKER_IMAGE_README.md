# CareCloud AI Agent Docker Image

## Exported Image File
- **File**: `carecloud-agent-image.tar`
- **Size**: ~404MB
- **Image Name**: `agent-project-agent:latest`
- **Created**: September 14, 2025

## How to Use This Image

### Option 1: Load and Run Locally

```bash
# Load the image
docker load -i carecloud-agent-image.tar

# Run with Docker Compose (recommended)
docker-compose up -d

# Or run standalone
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key_here \
  -e DB_HOST=your_db_host \
  agent-project-agent:latest
```

### Option 2: Deploy to Google Cloud VM

```bash
# Copy to your VM
gcloud compute scp carecloud-agent-image.tar your-vm-name:/home/ubuntu/

# SSH to VM and load
gcloud compute ssh your-vm-name
docker load -i carecloud-agent-image.tar

# Run the container
docker run -d \
  --name carecloud-agent \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key_here \
  -e DB_HOST=localhost \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres123 \
  -e DB_NAME=carecloud \
  agent-project-agent:latest
```

### Option 3: Push to Container Registry

```bash
# Load the image
docker load -i carecloud-agent-image.tar

# Tag for your registry
docker tag agent-project-agent:latest gcr.io/your-project/carecloud-agent:v1

# Push to registry
docker push gcr.io/your-project/carecloud-agent:v1
```

## Environment Variables Required

```bash
GEMINI_API_KEY=your_gemini_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres123
DB_NAME=carecloud
LLM_MODEL_NAME=gemini-1.5-flash
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

## API Endpoints

Once running, the API will be available at:
- **Base URL**: `http://localhost:8000`
- **Health Check**: `GET /health`
- **AI Query**: `POST /query`
- **API Docs**: `GET /docs`

## Included Components

✅ **LangChain Agent** - Main AI agent with Gemini integration
✅ **Toolbox Agent** - File management and calculation tools
✅ **EmbedChain Retriever** - RAG with vector search
✅ **NanoPQ Retriever** - Efficient vector similarity search
✅ **FastAPI Application** - REST API with automatic docs
✅ **Health Checks** - Built-in monitoring
✅ **Structured Logging** - Comprehensive logging system

## File Contents

This image contains the complete CareCloud AI Agent system:
- Python 3.11 application
- All dependencies (LangChain, Gemini, etc.)
- Application code and configurations
- Health check endpoints
- Production optimizations

Ready for deployment! 🚀
