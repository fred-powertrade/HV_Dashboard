#!/bin/bash

# HV Screener Setup Script
# This script sets up the Historical Volatility Screener application

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Historical Volatility Screener - Setup Script          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python installation
echo "📋 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python $PYTHON_VERSION found"
echo ""

# Check pip
echo "📋 Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip is not installed. Installing pip..."
    python3 -m ensurepip --upgrade
fi
echo "✓ pip found"
echo ""

# Create virtual environment (optional but recommended)
read -p "🔧 Create a virtual environment? (recommended) [y/N]: " create_venv
if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    echo "✓ Virtual environment created and activated"
    echo ""
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
    echo ""
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check for asset_list.csv
echo "📄 Checking for asset_list.csv..."
if [ -f "asset_list.csv" ]; then
    echo "✓ asset_list.csv found"
    NUM_ASSETS=$(wc -l < asset_list.csv)
    echo "  → $((NUM_ASSETS - 1)) assets loaded"
else
    echo "⚠️  asset_list.csv not found"
    echo "  → You can upload it via the web interface when running the app"
fi
echo ""

# Create .streamlit directory if it doesn't exist
if [ ! -d ".streamlit" ]; then
    echo "📁 Creating .streamlit configuration directory..."
    mkdir -p .streamlit
    
    # Copy config if template exists
    if [ -f ".streamlit/config.toml" ]; then
        echo "✓ Configuration files already exist"
    fi
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Setup Complete! 🎉                                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "To run the application:"
echo ""
if [[ $create_venv =~ ^[Yy]$ ]]; then
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "  1. Activate virtual environment: venv\\Scripts\\activate"
    else
        echo "  1. Activate virtual environment: source venv/bin/activate"
    fi
fi
echo "  2. Run the app: streamlit run hv_screener_enhanced.py"
echo ""
echo "The app will open in your browser at http://localhost:8501"
echo ""
echo "For deployment instructions, see DEPLOYMENT_GUIDE.md"
echo ""
