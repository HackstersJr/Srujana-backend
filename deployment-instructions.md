# CareCloud AI Agent - Public Registry Deployment

## Image Information
- **Registry**: docker.io
- **Repository**: bluni/carecloud-agent
- **Tag**: latest
- **Full Image Name**: docker.io/bluni/carecloud-agent:latest

## Quick Deployment Commands

### Using Docker Compose
`yaml
version: '3.8'
services:
  carecloud-agent:
    image: docker.io/bluni/carecloud-agent:latest
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
`

### Using Docker Run
`powershell
# Run the agent
docker run -d `
  --name carecloud-agent `
  -p 8000:8000 `
  -e GEMINI_API_KEY=your_gemini_api_key_here `
  -e DB_HOST=host.docker.internal `
  -e DB_USER=postgres `
  -e DB_PASSWORD=postgres123 `
  -e DB_NAME=carecloud `
  docker.io/bluni/carecloud-agent:latest

# Run PostgreSQL (if not using external DB)
docker run -d `
  --name postgres `
  -e POSTGRES_DB=carecloud `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres123 `
  -p 5432:5432 `
  postgres:15-alpine

# Run Redis (optional)
docker run -d `
  --name redis `
  -p 6379:6379 `
  redis:7-alpine
`

## API Endpoints
- **Health Check**: GET http://localhost:8000/health
- **AI Query**: POST http://localhost:8000/query
- **API Docs**: GET http://localhost:8000/docs

## Required Environment Variables
- GEMINI_API_KEY: Your Google Gemini API key
- DB_HOST: Database host (default: localhost)
- DB_USER: Database user (default: postgres)
- DB_PASSWORD: Database password (default: postgres123)
- DB_NAME: Database name (default: carecloud)

## Pulling the Image
`powershell
docker pull docker.io/bluni/carecloud-agent:latest
`

---
*Generated on 09/14/2025 06:41:21*
