#!/bin/bash
# Developer setup script for Mac/Linux

set -e

echo "Setting up development environment..."

# 1. Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
fi

# 2. Activate venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Initialize pre-commit
if command -v pre-commit &> /dev/null; then
    pre-commit install
fi

# 5. Create data and log directories
mkdir -p data logs/deployments logs/workers

# 6. Create local .env from example
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ".env file created from .env.example"
fi

echo "Setup complete! Activate the environment with: source venv/bin/activate"
