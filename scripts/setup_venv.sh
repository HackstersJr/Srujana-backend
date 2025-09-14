#!/usr/bin/env bash
# setup_venv.sh - Setup virtual environment for the agent project

set -e

echo "🚀 Setting up virtual environment for Agent Project..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Virtual environment setup complete!"
echo ""
echo "To activate the virtual environment:"
echo "  - On Windows: venv\\Scripts\\activate"
echo "  - On Unix/macOS: source venv/bin/activate"
echo ""
echo "To deactivate: deactivate"
