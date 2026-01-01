# Validate local development environment setup for Windows
# PowerShell script

$ErrorActionPreference = "Continue"

Write-Host "🔍 Validating local development setup..." -ForegroundColor Cyan
Write-Host ""

$ERRORS = 0
$WARNINGS = 0

# Function to check if a command exists
function Test-CommandExists {
    param($Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Function to check if directory exists
function Test-Directory {
    param($Path)
    if (Test-Path -Path $Path -PathType Container) {
        Write-Host "✓ Directory exists: $Path" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ Directory missing: $Path" -ForegroundColor Red
        $script:ERRORS++
        return $false
    }
}

# Function to check if file exists
function Test-FileExists {
    param($Path)
    if (Test-Path -Path $Path -PathType Leaf) {
        Write-Host "✓ File exists: $Path" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ File missing: $Path" -ForegroundColor Red
        $script:ERRORS++
        return $false
    }
}

# 1. Check Python version
Write-Host "1. Checking Python version..."
if (Test-CommandExists python) {
    try {
        $pythonVersion = (python --version 2>&1) -replace "Python ", ""
        $versionParts = $pythonVersion.Split('.')
        $major = [int]$versionParts[0]
        $minor = [int]$versionParts[1]
        
        if ($major -ge 3 -and $minor -ge 12) {
            Write-Host "✓ Python $pythonVersion (>= 3.12 required)" -ForegroundColor Green
        } else {
            Write-Host "✗ Python $pythonVersion found, but 3.12+ required" -ForegroundColor Red
            $ERRORS++
        }
    } catch {
        Write-Host "✗ Unable to determine Python version" -ForegroundColor Red
        $ERRORS++
    }
} else {
    Write-Host "✗ Python not found" -ForegroundColor Red
    Write-Host "   Install Python 3.12+ from https://www.python.org/" -ForegroundColor Yellow
    $ERRORS++
}
Write-Host ""

# 2. Check for uv
Write-Host "2. Checking for uv package manager..."
if (Test-CommandExists uv) {
    try {
        $uvVersion = (uv --version 2>&1)
        Write-Host "✓ $uvVersion" -ForegroundColor Green
    } catch {
        Write-Host "⚠ uv found but version check failed" -ForegroundColor Yellow
        $WARNINGS++
    }
} else {
    Write-Host "⚠ uv not found (optional but recommended)" -ForegroundColor Yellow
    Write-Host "   Install: powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor Yellow
    $WARNINGS++
}
Write-Host ""

# 3. Check virtual environment
Write-Host "3. Checking virtual environment..."
if (Test-Path -Path ".venv" -PathType Container) {
    Write-Host "✓ Virtual environment exists: .venv" -ForegroundColor Green
    
    # Check if environment is activated
    if ($env:VIRTUAL_ENV) {
        Write-Host "✓ Virtual environment is activated" -ForegroundColor Green
    } else {
        Write-Host "⚠ Virtual environment not activated" -ForegroundColor Yellow
        Write-Host "   Run: .venv\Scripts\activate" -ForegroundColor Yellow
        $WARNINGS++
    }
} else {
    Write-Host "✗ Virtual environment not found" -ForegroundColor Red
    Write-Host "   Run: uv sync --extra dev" -ForegroundColor Yellow
    $ERRORS++
}
Write-Host ""

# 4. Check package installation
Write-Host "4. Checking package installation..."
try {
    $result = python -c "import src.shared_utils.config" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Package installed (src modules importable)" -ForegroundColor Green
    } else {
        Write-Host "✗ Package not installed in editable mode" -ForegroundColor Red
        Write-Host "   Run: uv pip install -e ." -ForegroundColor Yellow
        $ERRORS++
    }
} catch {
    Write-Host "✗ Package not installed in editable mode" -ForegroundColor Red
    Write-Host "   Run: uv pip install -e ." -ForegroundColor Yellow
    $ERRORS++
}
Write-Host ""

# 5. Check required directories
Write-Host "5. Checking required directories..."
Test-Directory "data\input" | Out-Null
Test-Directory "data\output" | Out-Null
Test-Directory "data\dev\input" | Out-Null
Test-Directory "data\dev\output" | Out-Null
Test-Directory "data\sample" | Out-Null
Test-Directory "logs" | Out-Null
Test-Directory "reports" | Out-Null
Test-Directory "sql" | Out-Null
Write-Host ""

# 6. Check configuration files
Write-Host "6. Checking configuration files..."
Test-FileExists "pyproject.toml" | Out-Null
Test-FileExists "prefect.yaml" | Out-Null
Test-FileExists ".env.example" | Out-Null

if (Test-FileExists ".env") {
    Write-Host "   Note: .env file exists (good for local development)" -ForegroundColor Green
} else {
    Write-Host "   Info: Copy .env.example to .env for local config" -ForegroundColor Yellow
    Write-Host "   Run: copy .env.example .env" -ForegroundColor Yellow
    $WARNINGS++
}
Write-Host ""

# 7. Check key dependencies
Write-Host "7. Checking key dependencies..."
$dependencies = @("prefect", "marimo", "polars", "pytest")
foreach ($dep in $dependencies) {
    try {
        $version = python -c "import $dep; print($dep.__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $dep ($version)" -ForegroundColor Green
        } else {
            Write-Host "✗ $dep not installed" -ForegroundColor Red
            $ERRORS++
        }
    } catch {
        Write-Host "✗ $dep not installed" -ForegroundColor Red
        $ERRORS++
    }
}
Write-Host ""

# 8. Check notebook files
Write-Host "8. Checking notebook files..."
$notebooks = @("notebooks\etl\daily_data_sync.py", "notebooks\reports\daily_summary.py")
foreach ($notebook in $notebooks) {
    Test-FileExists $notebook | Out-Null
}
Write-Host ""

# Summary
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

if ($ERRORS -eq 0 -and $WARNINGS -eq 0) {
    Write-Host "✓ All checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your environment is ready. Next steps:"
    Write-Host "  1. Start Prefect server: prefect server start"
    Write-Host "  2. Start Prefect worker: prefect worker start --pool windows-process-pool --type process"
    Write-Host "  3. Test a notebook: python notebooks\etl\daily_data_sync.py"
    exit 0
} elseif ($ERRORS -eq 0) {
    Write-Host "⚠ Setup complete with $WARNINGS warning(s)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "You can proceed, but consider addressing the warnings above."
    exit 0
} else {
    Write-Host "✗ Setup incomplete: $ERRORS error(s), $WARNINGS warning(s)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the errors above before proceeding."
    exit 1
}
