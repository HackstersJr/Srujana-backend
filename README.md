# CareCloud AI Agent System

A comprehensive AI agent system built with LangChain, integrating multiple retrievers (NanoPQ, EmbedChain), PostgreSQL database, and toolbox capabilities. Designed for healthcare AI applications with modular architecture and Docker deployment.

## 🚀 Features

- **Multi-Agent Architecture**: LangChain and Toolbox agents with different capabilities
- **Advanced Retrievers**: NanoPQ for efficient vector search, EmbedChain for RAG capabilities
- **Database Integration**: PostgreSQL with async support and connection pooling
- **Toolbox Integration**: Extensible tool system for enhanced agent capabilities
- **Docker Deployment**: Complete containerized deployment with Docker Compose
- **API Interface**: FastAPI-based REST API with auto-generated documentation
- **Console Mode**: Interactive command-line interface for development and testing
- **Comprehensive Logging**: Structured logging with multiple output formats
- **Environment Management**: Configuration through environment variables

## 📋 Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL (if running locally without Docker)
- OpenAI API key (for LLM functionality)

## 🛠️ Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd agent-project
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your OpenAI API key and other settings
   ```

3. **Deploy with Docker:**
   ```bash
   # On Linux/macOS
   ./scripts/deploy_docker.sh

   # On Windows (PowerShell)
   .\scripts\deploy_docker.ps1
   ```

4. **Access the system:**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Option 2: Local Development

1. **Setup development environment:**
   ```bash
   # On Linux/macOS
   ./scripts/setup_dev.sh

   # On Windows (PowerShell)
   .\scripts\setup_dev.ps1
   ```

2. **Activate virtual environment:**
   ```bash
   # On Linux/macOS
   source venv/bin/activate

   # On Windows
   .\venv\Scripts\Activate.ps1
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

4. **Run the system:**
   ```bash
   # Console mode
   python main.py --mode console

   # Server mode
   python main.py --mode server
   ```

## 🏗️ Architecture

```
agent-project/
├── agents/                 # Agent implementations
│   ├── __init__.py        # Agent module initialization
│   ├── base_agent.py      # Base agent class
│   ├── database_agent.py  # Database operations agent
│   ├── medicine_agent.py  # Medicine management agent
│   ├── patient_monitoring_agent.py # Patient monitoring agent
│   ├── stock_management_agent.py # Stock management agent
│   ├── appointment_agent.py # Appointment scheduling agent
│   ├── langchain_agent.py # LangChain agent implementation
│   ├── langgraph_agent.py # LangGraph agent implementation
│   └── toolbox_agent.py   # Toolbox agent implementation
├── retrievers/            # Retriever implementations
│   ├── base_retriever.py  # Base retriever class
│   ├── nanopq_retriever.py # NanoPQ vector retriever
│   └── embedchain_retriever.py # EmbedChain RAG retriever
├── services/              # Service layer
│   ├── db_service.py      # PostgreSQL database service
│   ├── toolbox_service.py # Tool management service
│   └── utils.py           # Utility functions
├── configs/               # Configuration management
│   ├── settings.py        # Application settings
│   └── logging_config.py  # Logging configuration
├── data/                  # Data storage
│   ├── input/            # Input data files
│   └── output/           # Output data files
├── tests/                 # Test suite
├── scripts/               # Setup and deployment scripts
├── main.py               # Application entry point
├── Dockerfile            # Docker image definition
└── docker-compose.yml    # Multi-container deployment
```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=carecloud

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# LLM Configuration
LLM_MODEL_NAME=gpt-3.5-turbo
LLM_TEMPERATURE=0.7

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### Advanced Configuration

The system uses Pydantic settings for type-safe configuration management. All settings can be configured through:

1. Environment variables
2. `.env` file
3. Direct configuration in `configs/settings.py`

## 📡 API Usage

### Health Check
```bash
curl http://localhost:8000/health
```

### Query Processing
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is artificial intelligence?", "agent_type": "langchain"}'
```

### Agent Status
```bash
curl http://localhost:8000/agents/status
```

## 🔍 Agent Types

### Medicine Agent
- Handles medicine inventory, stock levels, expiry tracking, and prescription management
- Specialized for pharmaceutical operations and drug information
- Access via `agent_type: "medicine"` or keywords like "medicine", "inventory", "prescription"

### Patient Monitoring Agent
- Monitors patient vitals, health metrics, and medical history
- Tracks health alerts and provides preventive care recommendations
- Access via `agent_type: "patient_monitoring"` or keywords like "patient", "vitals", "monitoring"

### Stock Management Agent
- Manages inventory levels, reorder alerts, and supplier relationships
- Handles stock transactions and supply chain optimization
- Access via `agent_type: "stock_management"` or keywords like "stock", "inventory", "reorder"

### Appointment Agent
- Manages appointment scheduling, rescheduling, and cancellations
- Handles calendar management and booking coordination
- Access via `agent_type: "appointment"` or keywords like "appointment", "schedule", "booking"

### Database Agent
- Executes SQL queries and manages database operations
- Provides data analysis and reporting capabilities
- Used internally by other specialized agents

### LangChain Agent
- Uses LangChain framework for agent orchestration
- Supports multiple tools and retrievers
- Optimized for complex reasoning tasks
- Access via `agent_type: "langchain"`

### Toolbox Agent
- Focused on tool usage and execution
- Modular tool system
- Extensible with custom tools
- Access via `agent_type: "toolbox"`

## 🗄️ Database Schema

The system automatically creates the following PostgreSQL tables:

- `agent_sessions`: Track agent sessions
- `agent_queries`: Store queries and responses
- `documents`: Store processed documents

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov=retrievers --cov=services

# Run specific test categories
pytest tests/ -m unit
pytest tests/ -m integration
```

## 📊 Monitoring and Logging

### Logging Levels
- `DEBUG`: Detailed diagnostic information
- `INFO`: General operational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical system failures

### Log Files
- Application logs: `logs/agent.log`
- Performance logs: Structured logging for metrics
- Error logs: Dedicated error tracking

## 🔄 Development Workflow

### Code Formatting
```bash
# Format code
black agents/ retrievers/ services/ configs/ main.py
isort agents/ retrievers/ services/ configs/ main.py

# Lint code
flake8 agents/ retrievers/ services/ configs/ main.py
mypy agents/ retrievers/ services/ configs/ main.py
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files
```

## 🐳 Docker Commands

```bash
# Build image
docker build -t carecloud-agent .

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f agent

# Scale services
docker-compose up -d --scale agent=3

# Stop services
docker-compose down

# Clean up
docker-compose down -v --rmi all
```

## 🔧 Troubleshooting

### Common Issues

1. **API Key Missing**
   ```
   Error: OpenAI API key not configured
   Solution: Set OPENAI_API_KEY in .env file
   ```

2. **Database Connection Failed**
   ```
   Error: Could not connect to PostgreSQL
   Solution: Check DB_HOST, DB_PORT, and credentials in .env
   ```

3. **Port Already in Use**
   ```
   Error: Port 8000 already in use
   Solution: Change SERVER_PORT in .env or stop conflicting service
   ```

4. **Memory Issues with Retrievers**
   ```
   Error: Out of memory during vector operations
   Solution: Reduce batch sizes in retriever configuration
   ```

### Debugging

1. **Enable Debug Logging**
   ```bash
   export LOG_LEVEL=DEBUG
   python main.py --mode console
   ```

2. **Check Service Health**
   ```bash
   curl http://localhost:8000/agents/status
   ```

3. **Database Connectivity**
   ```bash
   docker-compose exec postgres psql -U postgres -d carecloud -c "SELECT 1;"
   ```

## 🚀 Production Deployment

### Environment Preparation
1. Set `ENVIRONMENT=production` in `.env`
2. Configure proper database credentials
3. Set up SSL certificates for HTTPS
4. Configure monitoring and alerting

### Scaling Considerations
- Use load balancer for multiple agent instances
- Configure PostgreSQL for high availability
- Set up Redis for caching (optional)
- Monitor resource usage and adjust limits

### Security
- Change default passwords
- Use secrets management for API keys
- Configure firewall rules
- Enable audit logging

### Public Registry Deployment

For easy distribution and deployment across different environments, you can push the Docker image to a public container registry:

#### Supported Registries
- **Docker Hub** (docker.io) - General public distribution
- **Google Container Registry** (gcr.io) - Google Cloud integration
- **GitHub Container Registry** (ghcr.io) - GitHub ecosystem integration

#### Quick Registry Deployment

1. **Deploy to Docker Hub:**
   ```bash
   # Linux/macOS
   export USERNAME=your-dockerhub-username
   ./scripts/deploy-registry.sh

   # Windows PowerShell
   .\scripts\deploy-registry.ps1 -Username your-dockerhub-username
   ```

2. **Deploy to other registries:**
   ```bash
   # Google Container Registry
   export REGISTRY=gcr.io USERNAME=your-gcp-project-id
   ./scripts/deploy-registry.sh

   # GitHub Container Registry
   export REGISTRY=ghcr.io USERNAME=your-github-username
   ./scripts/deploy-registry.sh
   ```

3. **Pull and deploy from anywhere:**
   ```bash
   # Pull the image
   docker pull your-registry/carecloud-agent:latest

   # Deploy with Docker Compose
   docker-compose up -d
   ```

See [`REGISTRY_DEPLOYMENT_README.md`](REGISTRY_DEPLOYMENT_README.md) for detailed instructions, CI/CD integration examples, and security considerations.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation for API changes
- Use type hints for all functions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review the API documentation at `/docs` endpoint

## 🔮 Roadmap

- [ ] Add support for additional LLM providers
- [ ] Implement real-time monitoring dashboard
- [ ] Add support for custom embedding models
- [ ] Implement advanced caching strategies
- [ ] Add support for multi-tenant deployments
- [ ] Integrate with vector databases (Pinecone, Weaviate)
- [ ] Add support for streaming responses
- [ ] Implement advanced security features

---

**Built with ❤️ for the CareCloud AI ecosystem**
