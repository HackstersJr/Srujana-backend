# setup_venv.ps1 - PowerShell script to setup virtual environment

Write-Host "🚀 Setting up virtual environment for Agent Project..." -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "✅ Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed. Please install Python 3.8 or higher." -ForegroundColor Red
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

Write-Host "✅ Virtual environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "To deactivate: deactivate" -ForegroundColor Cyan
