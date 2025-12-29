#!/bin/bash

# Setup script for AI Sustainability Data Extraction System

echo "=================================="
echo "ESG Data Extraction System Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
echo "Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file from template"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your OpenRouter API key"
    echo "   Get your key from: https://openrouter.ai/keys"
else
    echo "✓ .env file already exists"
fi

# Create required directories
echo ""
echo "Creating directories..."
mkdir -p reports
mkdir -p outputs
mkdir -p data
echo "✓ Directories created"

# Test imports
echo ""
echo "Testing system setup..."
python test_setup.py

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your OpenRouter API key"
echo "2. Download PDF reports to the reports/ directory"
echo "3. Run extraction: python main.py --pdf reports/YOUR_FILE.pdf --company 'Company' --year 2024"
echo "   Or start API: python api.py"
echo ""
echo "For more information, see README.md"
echo ""
