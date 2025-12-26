<#
.SYNOPSIS
    Configures Prefect Server and Worker as Windows Services using NSSM.
    
.PARAMETER OfflineSource
    Path to downloaded assets (containing NSSM zip). Defaults to "C:\PrefectOffline".

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
$NssmZip = "$OfflineSource\nssm.zip"
$NssmInstallDir = "C:\nssm"
$VenvPython = "$InstallDir\venv\Scripts\python.exe"
$PrefectExe = "$InstallDir\venv\Scripts\prefect.exe"

# 1. Install/Extract NSSM
if (-not (Test-Path "$NssmInstallDir\nssm.exe")) {
    Write-Host "Extracting NSSM..." -ForegroundColor Cyan
    Expand-Archive -Path $NssmZip -DestinationPath $NssmInstallDir -Force
    # Find the exe (it's usually in a subfolder like nssm-2.24...\win64)
    $NssmExePath = Get-ChildItem "$NssmInstallDir" -Recurse -Filter "nssm.exe" | Where-Object { $_.DirectoryName -like "*win64*" } | Select-Object -First 1
    if ($NssmExePath) {
        Copy-Item $NssmExePath.FullName "$NssmInstallDir\nssm.exe"
        Write-Host "NSSM installed to $NssmInstallDir\nssm.exe"
    } else {
        Throw "Could not locate nssm.exe after extraction."
    }
}

$NssmExe = "$NssmInstallDir\nssm.exe"
# Add to PATH for convenience
$env:PATH = "$env:PATH;$NssmInstallDir"

# 2. Configure Prefect Server Service
$ServerServiceName = "PrefectServer"
Write-Host "Configuring Service: $ServerServiceName..." -ForegroundColor Cyan

# Check if exists
if (Get-Service $ServerServiceName -ErrorAction SilentlyContinue) {
    Write-Host "Service $ServerServiceName already exists. Skipping install (configure update only)." -ForegroundColor Yellow
} else {
    & $NssmExe install $ServerServiceName $VenvPython
}

# Apply Configuration
& $NssmExe set $ServerServiceName AppParameters "-m prefect server start --host 127.0.0.1 --port 4200"
& $NssmExe set $ServerServiceName AppDirectory $InstallDir
& $NssmExe set $ServerServiceName DisplayName "Prefect Orchestration Server"
& $NssmExe set $ServerServiceName Description "Prefect 3.x workflow orchestration server"
& $NssmExe set $ServerServiceName Start SERVICE_AUTO_START

# Env Vars
& $NssmExe set $ServerServiceName AppEnvironmentExtra `
    "PREFECT_HOME=$InstallDir\data" `
    "PREFECT_SERVER_API_HOST=127.0.0.1" `
    "PREFECT_SERVER_API_PORT=4200" `
    "PYTHONUNBUFFERED=1" `
    "PYTHONIOENCODING=UTF-8"

# Logging & Rotation
& $NssmExe set $ServerServiceName AppStdout "$InstallDir\Logs\server-stdout.log"
& $NssmExe set $ServerServiceName AppStderr "$InstallDir\Logs\server-stderr.log"
& $NssmExe set $ServerServiceName AppRotateFiles 1
& $NssmExe set $ServerServiceName AppRotateOnline 1
& $NssmExe set $ServerServiceName AppRotateBytes 10485760

# Restart/Recovery
& $NssmExe set $ServerServiceName AppThrottle 5000
& $NssmExe set $ServerServiceName AppExit Default Restart
& $NssmExe set $ServerServiceName AppRestartDelay 10000

# Start Server
Write-Host "Starting Prefect Server..." -ForegroundColor Cyan
& $NssmExe start $ServerServiceName
# Wait for startup
Write-Host "Waiting 20 seconds for server startup..."
Start-Sleep -Seconds 20

# 3. Create Work Pool
# We need to use the venv's prefect and set API URL explicitly since we haven't set machine env vars
$env:PREFECT_API_URL = "http://127.0.0.1:4200/api"
$env:PREFECT_HOME = "$InstallDir\data"

Write-Host "Creating Work Pool: $WorkPoolName..." -ForegroundColor Cyan
try {
    & $PrefectExe work-pool create $WorkPoolName --type process
} catch {
    Write-Host "Work pool creation might have failed or already exists. Continuing..." -ForegroundColor Yellow
}

# 4. Configure Prefect Worker Service
$WorkerServiceName = "PrefectWorker"
Write-Host "Configuring Service: $WorkerServiceName..." -ForegroundColor Cyan

if (Get-Service $WorkerServiceName -ErrorAction SilentlyContinue) {
    Write-Host "Service $WorkerServiceName already exists. Skipping install." -ForegroundColor Yellow
} else {
    & $NssmExe install $WorkerServiceName $VenvPython
}

& $NssmExe set $WorkerServiceName AppParameters "-m prefect worker start --pool $WorkPoolName --type process"
& $NssmExe set $WorkerServiceName AppDirectory "$InstallDir\Flows"
& $NssmExe set $WorkerServiceName DisplayName "Prefect Worker - Process Pool"
& $NssmExe set $WorkerServiceName Start SERVICE_DELAYED_AUTO_START
& $NssmExe set $WorkerServiceName DependOnService $ServerServiceName

# Worker Env Vars
& $NssmExe set $WorkerServiceName AppEnvironmentExtra `
    "PREFECT_API_URL=http://127.0.0.1:4200/api" `
    "PREFECT_HOME=$InstallDir\data" `
    "PYTHONUNBUFFERED=1" `
    "PYTHONIOENCODING=UTF-8"

# Logging
& $NssmExe set $WorkerServiceName AppStdout "$InstallDir\Logs\worker-stdout.log"
& $NssmExe set $WorkerServiceName AppStderr "$InstallDir\Logs\worker-stderr.log"
& $NssmExe set $WorkerServiceName AppRotateFiles 1
& $NssmExe set $WorkerServiceName AppRotateOnline 1
& $NssmExe set $WorkerServiceName AppRotateBytes 10485760

Write-Host "Starting Worker..."
& $NssmExe start $WorkerServiceName

Write-Host "=== Services Configured ===" -ForegroundColor Green
& $NssmExe status $ServerServiceName
& $NssmExe status $WorkerServiceName
