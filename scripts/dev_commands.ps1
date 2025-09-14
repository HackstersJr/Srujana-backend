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
