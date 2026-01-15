#!/bin/bash
# Setup script for Parallax Index virtual environment
# Linux/macOS version

set -e

echo "=========================================="
echo "Parallax Index - Virtual Environment Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_CMD=""

if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python not found"
    exit 1
fi

VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $VERSION"

# Check if version is 3.12+
MAJOR=$(echo $VERSION | cut -d. -f1)
MINOR=$(echo $VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 12 ]); then
    echo "❌ Error: Python 3.12 or higher is required"
    echo "   Current version: $VERSION"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing venv..."
        rm -rf venv
        $PYTHON_CMD -m venv venv
        echo "✓ Virtual environment recreated"
    else
        echo "Using existing virtual environment"
    fi
else
    $PYTHON_CMD -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Verify installation
echo ""
echo "Verifying installation..."
python setup_check.py

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start the application:"
echo "  python main.py"
echo ""
echo "Or use VS Code tasks:"
echo "  Cmd/Ctrl+Shift+P → Tasks: Run Task → Run: Start Application"
echo ""
