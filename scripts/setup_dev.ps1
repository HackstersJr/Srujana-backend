# Development setup script for CareCloud AI Agent (PowerShell)

Write-Host "🛠️  Setting up CareCloud AI Agent development environment..." -ForegroundColor Green

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    Write-Host "🐍 Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Check if we're in the correct directory
if (-not (Test-Path "requirements.txt")) {
    Write-Host "❌ requirements.txt not found. Please run this script from the project root." -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate virtual environment
Write-Host "🔄 Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "⬆️  Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host "📚 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Install development dependencies
Write-Host "🔧 Installing development dependencies..." -ForegroundColor Yellow
pip install pytest pytest-asyncio pytest-cov black flake8 isort mypy pre-commit

# Create .env file from template
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please edit .env file with your configuration." -ForegroundColor Yellow
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Yellow
$directories = @("data\input", "data\output", "logs", "tests")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Create placeholder files
Write-Host "📄 Creating placeholder files..." -ForegroundColor Yellow
@("data\input\.gitkeep", "data\output\.gitkeep", "logs\.gitkeep") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType File -Path $_ -Force | Out-Null
    }
}

# Setup pre-commit hooks
Write-Host "🪝 Setting up pre-commit hooks..." -ForegroundColor Yellow
try {
    pre-commit install
} catch {
    Write-Host "⚠️  Could not install pre-commit hooks" -ForegroundColor Yellow
}

# Run initial code formatting
Write-Host "🎨 Formatting code..." -ForegroundColor Yellow
try {
    black agents/ retrievers/ services/ configs/ main.py
    isort agents/ retrievers/ services/ configs/ main.py
} catch {
    Write-Host "⚠️  Code formatting failed (this is okay for first setup)" -ForegroundColor Yellow
}

# Create test configuration
if (-not (Test-Path "pytest.ini")) {
    Write-Host "📝 Creating pytest configuration..." -ForegroundColor Yellow
    @"
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
"@ | Out-File -FilePath "pytest.ini" -Encoding UTF8
}

# Create basic test files
if (-not (Test-Path "tests\test_agents.py")) {
    Write-Host "📝 Creating basic test files..." -ForegroundColor Yellow
    @"
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
"@ | Out-File -FilePath "tests\test_agents.py" -Encoding UTF8

    @"
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
"@ | Out-File -FilePath "tests\conftest.py" -Encoding UTF8
}

# Create PowerShell script for common tasks
if (-not (Test-Path "scripts\dev_commands.ps1")) {
    Write-Host "📝 Creating development commands script..." -ForegroundColor Yellow
    @"
# Development commands for CareCloud AI Agent

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host "  Install-Dependencies     - Install dependencies" -ForegroundColor White
    Write-Host "  Run-Tests               - Run tests" -ForegroundColor White
    Write-Host "  Run-Lint                - Run linting" -ForegroundColor White
    Write-Host "  Format-Code             - Format code" -ForegroundColor White
    Write-Host "  Clean-Project           - Clean up generated files" -ForegroundColor White
    Write-Host "  Start-Dev               - Run in development mode" -ForegroundColor White
    Write-Host "  Build-Docker            - Build Docker image" -ForegroundColor White
    Write-Host "  Run-Docker              - Run with Docker" -ForegroundColor White
}

function Install-Dependencies {
    pip install -r requirements.txt
}

function Run-Tests {
    pytest tests/ -v
}

function Run-Lint {
    flake8 agents/ retrievers/ services/ configs/ main.py
    mypy agents/ retrievers/ services/ configs/ main.py --ignore-missing-imports
}

function Format-Code {
    black agents/ retrievers/ services/ configs/ main.py
    isort agents/ retrievers/ services/ configs/ main.py
}

function Clean-Project {
    Get-ChildItem -Path . -Include "*.pyc" -Recurse | Remove-Item -Force
    Get-ChildItem -Path . -Include "__pycache__" -Directory -Recurse | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Include ".pytest_cache" -Directory -Recurse | Remove-Item -Recurse -Force
    if (Test-Path ".coverage") { Remove-Item ".coverage" -Force }
    if (Test-Path "htmlcov") { Remove-Item "htmlcov" -Recurse -Force }
}

function Start-Dev {
    python main.py --mode console
}

function Build-Docker {
    docker build -t carecloud-agent .
}

function Run-Docker {
    docker-compose up -d
}

# Show help by default
Show-Help
"@ | Out-File -FilePath "scripts\dev_commands.ps1" -Encoding UTF8
}

# Create .gitignore if it doesn't exist
if (-not (Test-Path ".gitignore")) {
    Write-Host "📝 Creating .gitignore..." -ForegroundColor Yellow
    @"
# Python
__pycache__/
*.py[cod]
*`$py.class
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
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
}

Write-Host ""
Write-Host "✅ Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Activate virtual environment: .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  2. Edit .env file with your configuration" -ForegroundColor White
Write-Host "  3. Run tests: pytest tests/ -v" -ForegroundColor White
Write-Host "  4. Start development: python main.py --mode console" -ForegroundColor White
Write-Host ""
Write-Host "Development commands available in scripts\dev_commands.ps1" -ForegroundColor Cyan
Write-Host ""
