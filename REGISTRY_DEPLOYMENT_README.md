# Public Container Registry Deployment Guide

This guide explains how to deploy the CareCloud AI Agent Docker image to a public container registry for easy distribution and deployment.

## Supported Registries

The deployment scripts support the following public container registries:

### Docker Hub (docker.io)
- **Free tier**: Available
- **Public repositories**: Free
- **Private repositories**: Paid
- **Best for**: General public distribution

### Google Container Registry (gcr.io)
- **Free tier**: 500MB storage, 5GB bandwidth/month
- **Integration**: Native Google Cloud integration
- **Best for**: Google Cloud deployments

### GitHub Container Registry (ghcr.io)
- **Free tier**: Unlimited public repositories
- **Integration**: GitHub Actions, GitHub Packages
- **Best for**: Open source projects with GitHub

## Prerequisites

1. **Docker Desktop** installed and running
2. **Account** on your chosen registry platform
3. **Access token** or credentials for authentication
4. **carecloud-agent-image.tar** file in the project root

## Quick Start

### For Docker Hub

```bash
# Linux/macOS
export USERNAME=your-dockerhub-username
./scripts/deploy-registry.sh

# Windows PowerShell
.\scripts\deploy-registry.ps1 -Username your-dockerhub-username
```

### For Google Container Registry

```bash
# Linux/macOS
export REGISTRY=gcr.io
export USERNAME=your-gcp-project-id
./scripts/deploy-registry.sh

# Windows PowerShell
.\scripts\deploy-registry.ps1 -Registry gcr.io -Username your-gcp-project-id
```

### For GitHub Container Registry

```bash
# Linux/macOS
export REGISTRY=ghcr.io
export USERNAME=your-github-username
./scripts/deploy-registry.sh

# Windows PowerShell
.\scripts\deploy-registry.ps1 -Registry ghcr.io -Username your-github-username
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REGISTRY` | Container registry URL | `docker.io` | No |
| `USERNAME` | Your registry username | - | **Yes** |
| `REPOSITORY` | Repository name | `carecloud-agent` | No |
| `TAG` | Image tag | `latest` | No |

## Authentication Setup

### Docker Hub
1. Create account at [hub.docker.com](https://hub.docker.com)
2. Generate access token in Account Settings > Security
3. Use username and token for authentication

### Google Container Registry
1. Enable Container Registry API in GCP Console
2. Install Google Cloud SDK
3. Authenticate: `gcloud auth login`
4. Configure Docker: `gcloud auth configure-docker`

### GitHub Container Registry
1. Create Personal Access Token with `packages` scope
2. Use your GitHub username and the token

## Generated Files

After successful deployment, the script generates:

- **`deployment-instructions.md`**: Complete deployment guide with:
  - Docker Compose configuration
  - Docker run commands
  - Environment variables
  - API endpoints documentation

## Deployment Examples

### Docker Compose (Recommended)

```yaml
version: '3.8'
services:
  carecloud-agent:
    image: docker.io/yourusername/carecloud-agent:latest
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=your_gemini_api_key_here
      - DB_HOST=postgres
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

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: carecloud-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: carecloud-agent
  template:
    metadata:
      labels:
        app: carecloud-agent
    spec:
      containers:
      - name: carecloud-agent
        image: docker.io/yourusername/carecloud-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: GEMINI_API_KEY
          value: "your_gemini_api_key_here"
        - name: DB_HOST
          value: "postgres-service"
        - name: DB_USER
          value: "postgres"
        - name: DB_PASSWORD
          value: "postgres123"
        - name: DB_NAME
          value: "carecloud"
---
apiVersion: v1
kind: Service
metadata:
  name: carecloud-agent-service
spec:
  selector:
    app: carecloud-agent
  ports:
    - port: 8000
      targetPort: 8000
  type: LoadBalancer
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Registry
on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_TOKEN }}

    - name: Build and push
      run: |
        docker load -i carecloud-agent-image.tar
        docker tag $(docker images -q agent-project-agent) ${{ secrets.DOCKER_USERNAME }}/carecloud-agent:${{ github.ref_name }}
        docker push ${{ secrets.DOCKER_USERNAME }}/carecloud-agent:${{ github.ref_name }}
```

### Google Cloud Build

```yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['load', '-i', 'carecloud-agent-image.tar']

- name: 'gcr.io/cloud-builders/docker'
  args: ['tag', 'agent-project-agent', 'gcr.io/$PROJECT_ID/carecloud-agent:$TAG_NAME']

- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$PROJECT_ID/carecloud-agent:$TAG_NAME']
```

## Security Considerations

1. **Never commit credentials** to version control
2. **Use access tokens** instead of passwords
3. **Rotate tokens regularly** in production
4. **Use private repositories** for sensitive deployments
5. **Scan images** for vulnerabilities before deployment

## Troubleshooting

### Common Issues

**"unauthorized: authentication required"**
- Check your registry credentials
- Ensure you're using the correct username/token
- Verify token permissions

**"manifest unknown"**
- Check if the image was pushed successfully
- Verify the image name and tag
- Try pulling with `docker pull <image-name>`

**"no space left on device"**
- Clear Docker cache: `docker system prune -a`
- Check available disk space
- Use Docker Desktop settings to increase disk allocation

### Getting Help

1. Check the generated `deployment-instructions.md`
2. Review Docker logs: `docker logs <container-name>`
3. Test locally first before registry deployment
4. Verify environment variables are set correctly

## Cost Optimization

### Docker Hub
- Use free public repositories for open source
- Upgrade to Pro for private repositories and teams

### Google Container Registry
- First 5GB bandwidth/month free
- $0.10/GB after free tier
- Regional storage for cost optimization

### GitHub Container Registry
- Unlimited free storage for public repositories
- 500MB storage for private repositories (free)
- Additional storage billed at $0.008/GB/month

## Next Steps

After registry deployment:

1. **Share the image** with your team or community
2. **Set up automated deployments** using CI/CD
3. **Monitor usage** and costs
4. **Update documentation** with new deployment methods
5. **Consider multi-arch builds** for broader compatibility

---

*For questions or issues, please check the main project documentation or create an issue in the repository.*
