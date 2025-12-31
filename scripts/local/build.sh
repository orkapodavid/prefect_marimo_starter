#!/bin/bash
set -e

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: '$1' is not installed or not in PATH."
        exit 1
    fi
}

echo "Starting build process..."

# 0. Check dependencies
echo "Checking dependencies..."
check_command ruff
check_command pytest
check_command marimo
check_command zip

# 1. Run Linting
echo "Running linting (ruff)..."
ruff check .

# 2. Run Formatting Check
echo "Running formatting check (ruff)..."
ruff format --check .

# 3. Run Tests
echo "Running tests..."
pytest

# 4. Run Marimo Check
echo "Running Marimo check..."
marimo check notebooks/

# 5. Create Deployment Package
echo "Creating deployment package (deploy.zip)..."
# Remove existing zip if any
rm -f deploy.zip

# Create zip excluding unnecessary files
# Included: src, notebooks, sql, prefect.yaml, pyproject.toml, README.md
# Excluded: git, pyc, pycache, venv, node_modules, pytest_cache
zip -r deploy.zip \
    src \
    notebooks \
    sql \
    prefect.yaml \
    pyproject.toml \
    README.md \
    -x "**/.git/*" \
    -x "**/*.pyc" \
    -x "**/__pycache__/*" \
    -x "**/.venv/*" \
    -x "**/node_modules/*" \
    -x "**/.pytest_cache/*"

echo "Build complete! deploy.zip created."
