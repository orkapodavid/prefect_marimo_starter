<#
.SYNOPSIS
    Installs Python and sets up the Prefect environment on the target Windows Server.
    
.PARAMETER OfflineSource
    Path to the directory containing downloaded assets (from Step 1).
    Defaults to "C:\PrefectOffline".
    
.PARAMETER InstallDir
    Target directory for the Prefect Server installation.
    Defaults to "C:\PrefectServer".
#>

param(
    [string]$OfflineSource = "C:\PrefectOffline",
    [string]$InstallDir = "C:\PrefectServer"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OfflineSource)) {
    Throw "Offline source directory not found: $OfflineSource"
}

# 1. Install Python
Write-Host "Installing Python (Silent)..." -ForegroundColor Cyan
$PythonInstaller = Get-ChildItem "$OfflineSource\python-*-amd64.exe" | Select-Object -First 1
if (-not $PythonInstaller) { Throw "Python installer not found in $OfflineSource" }

# Install to C:\Python312 (or similar based on version)
# We parse version from filename for the target dir
if ($PythonInstaller.Name -match "python-(\d+\.\d+)") {
    $PyVerShort = $matches[1].Replace(".", "")
    $PythonTargetDir = "C:\Python$PyVerShort"
} else {
    $PythonTargetDir = "C:\Python312"
}

Start-Process -Wait -FilePath $PythonInstaller.FullName -ArgumentList `
    "/quiet", `
    "InstallAllUsers=1", `
    "PrependPath=1", `
    "Include_pip=1", `
    "Include_test=0", `
    "TargetDir=$PythonTargetDir"

Write-Host "Python installed to $PythonTargetDir" -ForegroundColor Green
$PythonExe = "$PythonTargetDir\python.exe"

# 2. Create Directory Structure
Write-Host "Creating directory structure at $InstallDir..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\Logs" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\Flows" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\data" | Out-Null # For DB/Config

# 3. Create Virtual Environment
Write-Host "Creating virtual environment..." -ForegroundColor Cyan
& $PythonExe -m venv "$InstallDir\venv"

# 4. Install Dependencies from Offline Wheels
Write-Host "Installing Prefect and dependencies..." -ForegroundColor Cyan
$PipExe = "$InstallDir\venv\Scripts\pip.exe"
$WheelsDir = "$OfflineSource\wheels"

# Note: We must install the app code FIRST to resolve deps, or install deps then app.
# Since we bundle the app in step 5, we need to reorder or copy first.
# IMPROVEMENT: Let's copy app code (Step 5) BEFORE installing deps (Step 4) so we can 'pip install .'

# Move Step 5 (Copy App) Up here conceptually, but for minimal diff:
# We will just assume app is copied in next block, let's swap the blocks in valid PowerShell execution order via variable or just do it.
# Actually, I should reorder the script content to be logical.
# For now, I will change this block to installing generic prefect, AND THEN after copy, install the app.
# BUT, if I install prefect here, I might miss deps if I don't install the project.
# Better: Just install 'prefect' here as a baseline, and then `pip install --no-index ... .` after copying.
# Let's keep this block installing 'prefect' to ensure the base is there, and add 'pip install .' in step 5.

& $PipExe install --no-index --find-links=$WheelsDir prefect

# Verify
$PrefectExe = "$InstallDir\venv\Scripts\prefect.exe"
& $PrefectExe version

# 5. Install Application Code
Write-Host "Installing application code..." -ForegroundColor Cyan
$AppSource = Join-Path $OfflineSource "app"
if (Test-Path $AppSource) {
    Copy-Item -Path "$AppSource\*" -Destination $InstallDir -Recurse -Force
    Write-Host "Application code copied to $InstallDir"
    
    # Install the project itself (and remaining dependencies like polars)
    Write-Host "Installing project dependencies from wheels..."
    & $PipExe install --no-index --find-links=$WheelsDir -e $InstallDir
} else {
    Write-Host "WARNING: No bundled app code found at $AppSource" -ForegroundColor Yellow
}

Write-Host "=== Environment Setup Complete ===" -ForegroundColor Green
Write-Host "Virtual Environment: $InstallDir\venv"
Write-Host "Next Step: Configure Services using 03_configure_services.ps1"
