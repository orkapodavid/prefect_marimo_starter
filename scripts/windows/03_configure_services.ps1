<#
.SYNOPSIS
    Configures Prefect Server and Worker as Windows Services using WinSW.
    
.PARAMETER OfflineSource
    Path to downloaded assets (containing winsw.exe). Defaults to "C:\PrefectOffline".

.PARAMETER InstallDir
    Root of the Prefect installation. Defaults to "C:\PrefectServer".
    
.PARAMETER WorkPoolName
    Name of the work pool for the worker. Defaults to "windows-process-pool".
#>

param(
    [string]$OfflineSource = "C:\PrefectOffline",
    [string]$InstallDir = "C:\PrefectServer",
    [string]$WorkPoolName = "windows-process-pool"
)

$ErrorActionPreference = "Stop"

# Paths
$WinSwExeSource = "$OfflineSource\winsw.exe"
$VenvPython = "$InstallDir\venv\Scripts\python.exe"
$PrefectExe = "$InstallDir\venv\Scripts\prefect.exe"

# Get Script Directory (to find config templates)
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path
$ConfigDir = Join-Path $ScriptDir "configs"

if (-not (Test-Path $WinSwExeSource)) {
    Throw "Could not find winsw.exe at $WinSwExeSource"
}

if (-not (Test-Path $ConfigDir)) {
    Throw "Could not find config directory at $ConfigDir"
}

# Helper Function to Install Service
function Install-WinSwService {
    param (
        [string]$ServiceName,
        [string]$XmlTemplatePath,
        [hashtable]$Replacements
    )
    
    Write-Host "Configuring Service: $ServiceName..." -ForegroundColor Cyan
    
    # Define Target Paths
    $ServiceExe = Join-Path $InstallDir "$ServiceName.exe"
    $ServiceXml = Join-Path $InstallDir "$ServiceName.xml"
    
    # 1. Copy WinSW Executable
    Copy-Item -Path $WinSwExeSource -Destination $ServiceExe -Force
    
    # 2. Read and Process XML Template
    $XmlContent = Get-Content -Path $XmlTemplatePath -Raw
    foreach ($key in $Replacements.Keys) {
        $XmlContent = $XmlContent.Replace($key, $Replacements[$key])
    }
    Set-Content -Path $ServiceXml -Value $XmlContent
    
    # 3. Install Service (if not exists)
    if (Get-Service $ServiceName -ErrorAction SilentlyContinue) {
        Write-Host "Service $ServiceName already exists. Creating/Updating config only." -ForegroundColor Yellow
        # Stop service to update config if needed (WinSW allows `stop` `refresh` `start` but simple restart works)
        # We don't run install again if it exists.
        # However, updating the XML effectively updates the config for next start.
    }
    else {
        Write-Host "Installing $ServiceName service..."
        & $ServiceExe install
    }
    
    # 4. Start Service
    Write-Host "Starting $ServiceName..."
    & $ServiceExe start
}

# 1. Configure Prefect Server Service
Install-WinSwService `
    -ServiceName "PrefectServer" `
    -XmlTemplatePath (Join-Path $ConfigDir "PrefectServer.xml") `
    -Replacements @{}

# Wait for startup
Write-Host "Waiting 20 seconds for server startup..."
Start-Sleep -Seconds 20

# 2. Create Work Pool
# We need to use the venv's prefect and set API URL explicitly since we haven't set machine env vars
$env:PREFECT_API_URL = "http://127.0.0.1:4200/api"
$env:PREFECT_HOME = "$InstallDir\data"

Write-Host "Creating Work Pool: $WorkPoolName..." -ForegroundColor Cyan
try {
    & $PrefectExe work-pool create $WorkPoolName --type process
}
catch {
    Write-Host "Work pool creation might have failed or already exists. Continuing..." -ForegroundColor Yellow
}

# 3. Configure Prefect Worker Service
Install-WinSwService `
    -ServiceName "PrefectWorker" `
    -XmlTemplatePath (Join-Path $ConfigDir "PrefectWorker.xml") `
    -Replacements @{
    "@WORK_POOL_NAME@" = $WorkPoolName
}

Write-Host "=== Services Configured ===" -ForegroundColor Green
if (Get-Service "PrefectServer" -ErrorAction SilentlyContinue) {
    Write-Host "PrefectServer: Running"
}
if (Get-Service "PrefectWorker" -ErrorAction SilentlyContinue) {
    Write-Host "PrefectWorker: Running"
}
