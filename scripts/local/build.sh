#!/bin/bash
set -e

echo "Starting build process..."

# 1. Run Linting
echo "Running linting (ruff)..."
ruff check .

# 2. Run Formatting Check
echo "Running formatting check (ruff)..."
ruff format --check .

# 3. Run Tests
echo "Running tests..."
# We need to install the project in editable mode if not already, but we assume environment is set
pytest

# 4. Run Marimo Check
echo "Running Marimo check..."
marimo check notebooks/

# 5. Create Deployment Package
echo "Creating deployment package (deploy.zip)..."
# Remove existing zip if any
rm -f deploy.zip

# Create zip excluding unnecessary files
# Using git ls-files to respect .gitignore, then filtering
# Or explicitly zipping required directories
zip -r deploy.zip src notebooks prefect.yaml pyproject.toml -x "**/.git/*" "**/*.pyc" "**/__pycache__/*" "**/.venv/*"

echo "Build complete! deploy.zip created."
