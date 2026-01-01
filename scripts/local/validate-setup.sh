#!/bin/bash
# Validate local development environment setup

set -e

echo "🔍 Validating local development setup..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if directory exists
check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Directory exists: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Directory missing: $1"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} File exists: $1"
        return 0
    else
        echo -e "${RED}✗${NC} File missing: $1"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# 1. Check Python version
echo "1. Checking Python version..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
        echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION (>= 3.12 required)"
    else
        echo -e "${RED}✗${NC} Python $PYTHON_VERSION found, but 3.12+ required"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}✗${NC} Python 3 not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 2. Check for uv
echo "2. Checking for uv package manager..."
if command_exists uv; then
    UV_VERSION=$(uv --version 2>&1 | head -n1)
    echo -e "${GREEN}✓${NC} $UV_VERSION"
else
    echo -e "${YELLOW}⚠${NC} uv not found (optional but recommended)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# 3. Check virtual environment
echo "3. Checking virtual environment..."
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment exists: .venv"
    
    # Check if environment is activated
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo -e "${GREEN}✓${NC} Virtual environment is activated"
    else
        echo -e "${YELLOW}⚠${NC} Virtual environment not activated"
        echo "   Run: source .venv/bin/activate"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}✗${NC} Virtual environment not found"
    echo "   Run: uv sync"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 4. Check package installation
echo "4. Checking package installation..."
if python3 -c "import src.shared_utils.config" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Package installed (src modules importable)"
else
    echo -e "${RED}✗${NC} Package not installed in editable mode"
    echo "   Run: uv pip install -e ."
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 5. Check required directories
echo "5. Checking required directories..."
check_directory "data/input"
check_directory "data/output"
check_directory "data/dev/input"
check_directory "data/dev/output"
check_directory "data/sample"
check_directory "logs"
check_directory "reports"
check_directory "sql"
echo ""

# 6. Check configuration files
echo "6. Checking configuration files..."
check_file "pyproject.toml"
check_file "prefect.yaml"
check_file ".env.example"

if check_file ".env"; then
    echo -e "   ${GREEN}Note:${NC} .env file exists (good for local development)"
else
    echo -e "   ${YELLOW}Info:${NC} Copy .env.example to .env for local config"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# 7. Check key dependencies
echo "7. Checking key dependencies..."
DEPS=("prefect" "marimo" "polars" "pytest")
for dep in "${DEPS[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        VERSION=$(python3 -c "import $dep; print($dep.__version__)" 2>/dev/null || echo "unknown")
        echo -e "${GREEN}✓${NC} $dep ($VERSION)"
    else
        echo -e "${RED}✗${NC} $dep not installed"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# 8. Check notebook files
echo "8. Checking notebook files..."
NOTEBOOKS=("notebooks/etl/daily_data_sync.py" "notebooks/reports/daily_summary.py")
for notebook in "${NOTEBOOKS[@]}"; do
    check_file "$notebook"
done
echo ""

# Summary
echo "================================"
echo "Validation Summary"
echo "================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Your environment is ready. Next steps:"
    echo "  1. Start Prefect server: prefect server start"
    echo "  2. Start Prefect worker: prefect worker start --pool windows-process-pool --type process"
    echo "  3. Test a notebook: python notebooks/etl/daily_data_sync.py"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Setup complete with $WARNINGS warning(s)${NC}"
    echo ""
    echo "You can proceed, but consider addressing the warnings above."
    exit 0
else
    echo -e "${RED}✗ Setup incomplete: $ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please fix the errors above before proceeding."
    exit 1
fi
