<#
.SYNOPSIS
    Deploy Prefect flows from Marimo notebooks.
.EXAMPLE
    .\deploy.ps1 -Environment prod
    .\deploy.ps1 -Environment dev -NotebookPath "notebooks/etl/daily_data_sync.py"
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,
    
    [string]$Branch = "main",
    [string]$NotebookPath = "",  # Deploy specific notebook, or all if empty
    [switch]$DryRun,
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$VenvPath = "$ProjectRoot\.venv"
if (-not (Test-Path $VenvPath)) {
    # Fallback for server structure where venv is inside root or handled differently
    if (Test-Path "$ProjectRoot\venv") { $VenvPath = "$ProjectRoot\venv" }
}

$LogFile = "$ProjectRoot\logs\deploy-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Log { param($Msg) 
    $Entry = "$(Get-Date -Format 'HH:mm:ss') $Msg"
    Write-Host $Entry
    Add-Content -Path $LogFile -Value $Entry
}

# Ensure log directory exists
if (-not (Test-Path "$ProjectRoot\logs")) {
    New-Item -ItemType Directory -Path "$ProjectRoot\logs" -Force | Out-Null
}

Log "=== Deployment Started ==="
Log "Environment: $Environment"
if ($Offline) { Log "Mode: Offline (Skipping Git)" }

# 1. Pull latest code (Skip if Offline)
Set-Location $ProjectRoot
$CommitHash = "OFFLINE"

if (-not $Offline) {
    Log "Pulling latest code..."
    git fetch origin $Branch
    git checkout $Branch
    git pull origin $Branch
    $CommitHash = git rev-parse --short HEAD
    Log "Now at commit: $CommitHash"
}

# 2. Activate virtual environment
Log "Activating virtual environment..."
& "$VenvPath\Scripts\Activate.ps1"

# 3. Update dependencies (Skip if Offline)
if (-not $Offline) {
    Log "Updating dependencies..."
    if (Test-Path "$ProjectRoot\requirements.txt") {
        pip install -r requirements.txt --quiet
    } elseif (Test-Path "$ProjectRoot\pyproject.toml") {
        pip install -e . --quiet
    }
}

# 4. Load environment config
$EnvFile = "$ProjectRoot\config\environments\$Environment.env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
    Log "Loaded config: $EnvFile"
}

# 5. Deploy flows
Log "Deploying Prefect flows..."
if ($DryRun) {
    Log "DRY RUN - would execute: prefect deploy"
} else {
    if ($NotebookPath) {
        # Deploy specific notebook
        $FlowName = [System.IO.Path]::GetFileNameWithoutExtension($NotebookPath)
        prefect deploy --name "$FlowName-$Environment"
    } else {
        # Deploy all
        prefect deploy --all
    }
}

Log "=== Deployment Complete ==="
Log "Commit: $CommitHash"
