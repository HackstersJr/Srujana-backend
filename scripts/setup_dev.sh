#!/usr/bin/env bash
# Development setup script for CareCloud AI Agent

set -e

echo "🛠️  Setting up CareCloud AI Agent development environment..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "🐍 Found Python $PYTHON_VERSION"

# Check if we're in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found. Please run this script from the project root."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "🔧 Installing development dependencies..."
pip install \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    isort \
    mypy \
    pre-commit

# Create .env file from template
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/input data/output logs tests

# Create placeholder files
echo "📄 Creating placeholder files..."
touch data/input/.gitkeep
touch data/output/.gitkeep
touch logs/.gitkeep

# Setup pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Run initial code formatting
echo "🎨 Formatting code..."
black agents/ retrievers/ services/ configs/ main.py
isort agents/ retrievers/ services/ configs/ main.py

# Create test configuration
if [ ! -f pytest.ini ]; then
    echo "📝 Creating pytest configuration..."
    cat > pytest.ini << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
    -ra
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
EOF
fi

# Create basic test files
if [ ! -f tests/test_agents.py ]; then
    echo "📝 Creating basic test files..."
    cat > tests/test_agents.py << 'EOF'
"""
Test cases for agent modules.
"""
import pytest
from agents.base_agent import BaseAgent


def test_base_agent_initialization():
    """Test BaseAgent initialization."""
    # This is a placeholder test
    assert True


@pytest.mark.asyncio
async def test_agent_lifecycle():
    """Test agent start/stop lifecycle."""
    # This is a placeholder test
    assert True
EOF

    cat > tests/conftest.py << 'EOF'
"""
Pytest configuration and fixtures.
"""
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
EOF
fi

# Create Makefile for common tasks
if [ ! -f Makefile ]; then
    echo "📝 Creating Makefile..."
    cat > Makefile << 'EOF'
.PHONY: help install test lint format clean dev docker-build docker-run

help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  clean       - Clean up generated files"
	@echo "  dev         - Run in development mode"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run with Docker"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

lint:
	flake8 agents/ retrievers/ services/ configs/ main.py
	mypy agents/ retrievers/ services/ configs/ main.py --ignore-missing-imports

format:
	black agents/ retrievers/ services/ configs/ main.py
	isort agents/ retrievers/ services/ configs/ main.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf .coverage htmlcov/

dev:
	python main.py --mode console

docker-build:
	docker build -t carecloud-agent .

docker-run:
	docker-compose up -d
EOF
fi

# Create .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environment
venv/
env/
ENV/

# Environment variables
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# Data
data/input/*
data/output/*
!data/input/.gitkeep
!data/output/.gitkeep

# Testing
.pytest_cache/
.coverage
htmlcov/

# Jupyter
.ipynb_checkpoints/

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite
EOF
fi

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Edit .env file with your configuration"
echo "  3. Run tests: make test"
echo "  4. Start development: make dev"
echo ""
echo "Useful commands:"
echo "  📋 Help: make help"
echo "  🧪 Test: make test"
echo "  🎨 Format: make format"
echo "  🔍 Lint: make lint"
echo ""
