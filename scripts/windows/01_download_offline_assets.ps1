<#
.SYNOPSIS
    Downloads all required assets for an offline Prefect deployment on Windows Server.
    Includes: Python installer, Prefect & dependencies (wheels), NSSM, IIS modules.

.PARAMETER Destination
    Directory to save downloaded files. Defaults to "C:\PrefectOffline".
    
.PARAMETER PythonVersion
    Python version to target. Defaults to "3.12.4".
#>

param(
    [string]$Destination = "C:\PrefectOffline",
    [string]$PythonVersion = "3.12.4"
)

$ErrorActionPreference = "Stop"

# Define Project Root (Assuming script is in scripts/windows/)
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path
# Resolve-Path might fail if the path doesn't exist, but we are in the repo.
# relative path from scripts/windows to root is ../..
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName

Write-Host "Project Root detected as: $ProjectRoot" -ForegroundColor Gray

# Create destination directory
if (-not (Test-Path $Destination)) {
    Write-Host "Creating directory: $Destination" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    New-Item -ItemType Directory -Force -Path "$Destination\wheels" | Out-Null
}

# 1. Download Python Installer
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$PythonInstaller = Join-Path $Destination "python-$PythonVersion-amd64.exe"
Write-Host "Downloading Python $PythonVersion from $PythonUrl..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonInstaller

# 2. Download WinSW (Service Wrapper)
$WinSwUrl = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
$WinSwExe = Join-Path $Destination "winsw.exe"
Write-Host "Downloading WinSW from $WinSwUrl..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $WinSwUrl -OutFile $WinSwExe

# 3. Download IIS Modules
# URL Rewrite
$UrlRewriteUrl = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
$UrlRewriteMsi = Join-Path $Destination "rewrite_amd64.msi"
Write-Host "Downloading URL Rewrite Module..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $UrlRewriteUrl -OutFile $UrlRewriteMsi

# ARR 3.0
$ArrUrl = "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi"
$ArrMsi = Join-Path $Destination "requestRouter_amd64.msi"
Write-Host "Downloading Application Request Routing..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $ArrUrl -OutFile $ArrMsi

# 4. Download Python Dependencies (Wheels)
Write-Host "Downloading Python dependencies (Wheels)..." -ForegroundColor Cyan
Write-Host "NOTE: This requires a working Python environment on the current machine." -ForegroundColor Yellow

# Create a temporary venv for clean download
$DownloadEnv = Join-Path $Destination "download-env"
if (Test-Path "python.exe") {
    $PythonCmd = "python.exe"
} else {
    $PythonCmd = "py" # Try 'py' launcher if python.exe not in path
}

Write-Host "Creating temp venv for dependency resolution..."
try {
    & $PythonCmd -m venv $DownloadEnv
} catch {
    Write-Host "Failed to create venv. Ensure python is in your PATH." -ForegroundColor Red
    exit 1
}

$PipCmd = Join-Path $DownloadEnv "Scripts\pip.exe"

Write-Host "Downloading pip wheels for Project from: $ProjectRoot"
# We target win_amd64 and the specified Python version
# Note: We point to ProjectRoot to get all dependencies defined in pyproject.toml
& $PipCmd download "$ProjectRoot" `
    --dest (Join-Path $Destination "wheels") `
    --platform win_amd64 `
    --python-version 3.12 `
    --only-binary=:all:

# 5. Bundle Project Source Code
Write-Host "Bundling project source code..." -ForegroundColor Cyan
$AppDest = Join-Path $Destination "app"
New-Item -ItemType Directory -Force -Path $AppDest | Out-Null

# Robocopy is more robust for exclusions, but Copy-Item is standard PowerShell.
# specific exclusions to keep the bundle clean
$Exclude = @('.git', '.venv', 'venv', '.idea', '.vscode', '__pycache__', 'node_modules', 'offline-packages', 'build', 'dist', '*.pyc', '.env')

Get-ChildItem -Path $ProjectRoot -Exclude $Exclude | ForEach-Object {
    if ($Exclude -notcontains $_.Name) {
        Copy-Item -Path $_.FullName -Destination $AppDest -Recurse -Force
    }
}

Write-Host "Project code bundled into: $AppDest"

Write-Host "=== Download Complete ===" -ForegroundColor Green
Write-Host "All assets are in: $Destination"
Write-Host "Copy this ENTIRE folder to your offline Windows Server."
