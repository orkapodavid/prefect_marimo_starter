# Deploying Prefect 3.x on Air-Gapped Windows Server 2019

Prefect 3.x can be successfully deployed on an offline Windows Server 2019 environment using pre-downloaded packages, NSSM for service management, and IIS as a secure reverse proxy with Windows Authentication. This guide provides complete step-by-step instructions for the entire deployment process, from Python installation through verification testing.

The deployment requires **Python 3.10 or higher** (3.12 recommended), approximately **60-80 wheel files** for offline installation, and uses SQLite by default with an optional path to PostgreSQL for production scale. Prefect 3.x does not support Microsoft SQL Server natively. The IIS reverse proxy provides enterprise authentication while blocking direct access to the Prefect API port.

---

## Phase 1: Pre-download all required files on an internet-connected machine

Before transferring to your air-gapped server, gather all necessary installers and packages on a machine with internet access.

### Python installer

Download the Python 3.12.x Windows installer (64-bit) from the official Python website. The embedded installer won't work for this deployment—use the full installer.

```powershell
# Create staging directory
mkdir C:\PrefectOffline

# Download Python 3.12 installer
$pythonUrl = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
Invoke-WebRequest -Uri $pythonUrl -OutFile "C:\PrefectOffline\python-3.12.4-amd64.exe"
```

### Prefect and all dependencies as wheel files

The `pip download` command retrieves Prefect and its **60-80 transitive dependencies** as wheel files. Key compiled dependencies like `orjson` and `pydantic-core` have pre-built Windows wheels available, so Visual Studio Build Tools are not required.

```powershell
# Create virtual environment for clean downloads
python -m venv C:\PrefectOffline\download-env
C:\PrefectOffline\download-env\Scripts\activate

# Download all Prefect dependencies for Windows x64 Python 3.12
pip download prefect --dest C:\PrefectOffline\wheels --platform win_amd64 --python-version 3.12 --only-binary=:all:

# If any packages lack binary wheels, download sources too
pip download prefect --dest C:\PrefectOffline\wheels --platform win_amd64 --python-version 3.12
```

The download produces approximately **150-200MB** of wheel files including these critical packages:

| Package | Purpose |
|---------|---------|
| `prefect-3.x.x-py3-none-any.whl` | Core Prefect package |
| `orjson-*.whl` | Fast JSON (Rust-compiled, Windows wheels available) |
| `pydantic_core-*.whl` | Pydantic internals (Rust-compiled) |
| `fastapi-*.whl` | API framework |
| `uvicorn-*.whl` | ASGI server |
| `sqlalchemy-*.whl` | Database ORM |
| `httpx-*.whl` | HTTP client |

### IIS modules for offline installation

Download URL Rewrite and Application Request Routing (ARR) modules:

```powershell
# URL Rewrite Module (x64)
$urlRewriteUrl = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
Invoke-WebRequest -Uri $urlRewriteUrl -OutFile "C:\PrefectOffline\rewrite_amd64.msi"

# Application Request Routing 3.0
$arrUrl = "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi"
Invoke-WebRequest -Uri $arrUrl -OutFile "C:\PrefectOffline\requestRouter_amd64.msi"
```

### NSSM service manager

Download the pre-release build **2.24-101** which resolves console window issues on Windows Server 2019:

```powershell
$nssmUrl = "https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip"
Invoke-WebRequest -Uri $nssmUrl -OutFile "C:\PrefectOffline\nssm-2.24-101.zip"
```

### Transfer to air-gapped server

Copy the entire `C:\PrefectOffline` directory to removable media and transfer to the target server.

---

## Phase 2: Python installation on the air-gapped server

Run all PowerShell commands as Administrator throughout this deployment.

### Install Python silently

```powershell
# Install Python 3.12 for all users with pip enabled
Start-Process -Wait -FilePath "C:\PrefectOffline\python-3.12.4-amd64.exe" -ArgumentList `
    "/quiet", `
    "InstallAllUsers=1", `
    "PrependPath=1", `
    "Include_pip=1", `
    "Include_test=0", `
    "TargetDir=C:\Python312"

# Verify installation
C:\Python312\python.exe --version
```

### Create Prefect virtual environment and install packages

```powershell
# Create project directory structure
New-Item -ItemType Directory -Force -Path "C:\PrefectServer"
New-Item -ItemType Directory -Force -Path "C:\PrefectServer\Logs"
New-Item -ItemType Directory -Force -Path "C:\PrefectServer\Flows"

# Create virtual environment
C:\Python312\python.exe -m venv C:\PrefectServer\venv

# Activate and install from offline wheels
C:\PrefectServer\venv\Scripts\activate

pip install --no-index --find-links=C:\PrefectOffline\wheels prefect

# Verify Prefect installation
prefect version
```

The installation should report Prefect **3.6.x or higher** with Python 3.12.

---

## Phase 3: Database configuration

### SQLite default configuration for quick prototyping

Prefect uses SQLite by default, requiring no additional setup. The database file is created automatically at first server start.

| Setting | Default Value |
|---------|---------------|
| Database location | `%USERPROFILE%\.prefect\prefect.db` |
| Connection URL | `sqlite+aiosqlite:///${PREFECT_HOME}/prefect.db` |
| Required SQLite version | 3.24.0+ (included with Python 3.12) |

For a custom database location:

```powershell
# Set custom PREFECT_HOME (where database and config are stored)
[System.Environment]::SetEnvironmentVariable("PREFECT_HOME", "C:\PrefectServer\data", "Machine")

# Or set specific database path
[System.Environment]::SetEnvironmentVariable("PREFECT_API_DATABASE_CONNECTION_URL", `
    "sqlite+aiosqlite:///C:/PrefectServer/data/prefect.db", "Machine")
```

### MS SQL Server is not supported—PostgreSQL as the production alternative

Prefect 3.x supports only **SQLite** and **PostgreSQL 13.0+** as database backends. Microsoft SQL Server is not supported. For production workloads requiring high concurrency, plan for PostgreSQL migration:

```powershell
# Future PostgreSQL configuration (when available)
[System.Environment]::SetEnvironmentVariable("PREFECT_API_DATABASE_CONNECTION_URL", `
    "postgresql+asyncpg://prefect_user:password@dbserver:5432/prefect", "Machine")

# PostgreSQL requires pg_trgm extension enabled:
# CREATE EXTENSION pg_trgm;
```

For the initial air-gapped deployment, SQLite works well for development and moderate workloads.

---

## Phase 4: Prefect server configuration

### Essential environment variables

Configure these system-wide environment variables:

```powershell
# Core Prefect configuration
[System.Environment]::SetEnvironmentVariable("PREFECT_HOME", "C:\PrefectServer\data", "Machine")
[System.Environment]::SetEnvironmentVariable("PREFECT_SERVER_API_HOST", "127.0.0.1", "Machine")
[System.Environment]::SetEnvironmentVariable("PREFECT_SERVER_API_PORT", "4200", "Machine")
[System.Environment]::SetEnvironmentVariable("PREFECT_API_URL", "http://127.0.0.1:4200/api", "Machine")

# Python encoding for Windows
[System.Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "UTF-8", "Machine")
[System.Environment]::SetEnvironmentVariable("PYTHONUNBUFFERED", "1", "Machine")

# Apply to current session
$env:PREFECT_HOME = "C:\PrefectServer\data"
$env:PREFECT_SERVER_API_HOST = "127.0.0.1"
$env:PREFECT_API_URL = "http://127.0.0.1:4200/api"
```

### Configuration file locations on Windows

| File/Directory | Path | Purpose |
|----------------|------|---------|
| PREFECT_HOME | `C:\PrefectServer\data` | Main config directory |
| SQLite database | `C:\PrefectServer\data\prefect.db` | Flow run data |
| Profiles | `C:\PrefectServer\data\profiles.toml` | Named configurations |
| Logs | `C:\PrefectServer\Logs` | Service output |

### Verify server starts manually

Before creating the Windows service, confirm the server runs correctly:

```powershell
# Activate virtual environment
C:\PrefectServer\venv\Scripts\activate

# Start server manually (Ctrl+C to stop)
prefect server start --host 127.0.0.1 --port 4200

# In another terminal, test the API
Invoke-WebRequest -Uri "http://localhost:4200/api/health" -Method GET
# Should return: true

Invoke-WebRequest -Uri "http://localhost:4200/api/hello" -Method GET
# Should return: 👋
```

---

## Phase 5: Windows service registration with NSSM

### Install NSSM

```powershell
# Extract NSSM
Expand-Archive -Path "C:\PrefectOffline\nssm-2.24-101.zip" -DestinationPath "C:\nssm"

# Add to system PATH
$nssmPath = "C:\nssm\nssm-2.24-101-g897c7ad\win64"
[System.Environment]::SetEnvironmentVariable("PATH", "$env:PATH;$nssmPath", "Machine")

# Refresh PATH in current session
$env:PATH = "$env:PATH;$nssmPath"
```

### Create Prefect Server service

```powershell
# Install service
nssm install PrefectServer "C:\PrefectServer\venv\Scripts\python.exe"

# Configure executable and arguments
nssm set PrefectServer AppParameters "-m prefect server start --host 127.0.0.1 --port 4200"
nssm set PrefectServer AppDirectory "C:\PrefectServer"

# Service identification
nssm set PrefectServer DisplayName "Prefect Orchestration Server"
nssm set PrefectServer Description "Prefect 3.x workflow orchestration server for data pipeline management"

# Startup configuration
nssm set PrefectServer Start SERVICE_AUTO_START

# Environment variables
nssm set PrefectServer AppEnvironmentExtra `
    "PREFECT_HOME=C:\PrefectServer\data" `
    "PREFECT_SERVER_API_HOST=127.0.0.1" `
    "PREFECT_SERVER_API_PORT=4200" `
    "PYTHONUNBUFFERED=1" `
    "PYTHONIOENCODING=UTF-8"

# Logging configuration
nssm set PrefectServer AppStdout "C:\PrefectServer\Logs\server-stdout.log"
nssm set PrefectServer AppStderr "C:\PrefectServer\Logs\server-stderr.log"
nssm set PrefectServer AppRotateFiles 1
nssm set PrefectServer AppRotateOnline 1
nssm set PrefectServer AppRotateBytes 10485760

# Recovery options - restart on failure
nssm set PrefectServer AppThrottle 5000
nssm set PrefectServer AppExit Default Restart
nssm set PrefectServer AppRestartDelay 10000

# Windows native recovery (belt and suspenders)
sc.exe failure PrefectServer reset= 86400 actions= restart/10000/restart/30000/restart/60000
```

### Create Prefect Worker service

```powershell
# First, create the work pool via API (server must be running)
nssm start PrefectServer
Start-Sleep -Seconds 15
C:\PrefectServer\venv\Scripts\prefect.exe work-pool create my-process-pool --type process

# Install worker service
nssm install PrefectWorker "C:\PrefectServer\venv\Scripts\python.exe"
nssm set PrefectWorker AppParameters "-m prefect worker start --pool my-process-pool --type process"
nssm set PrefectWorker AppDirectory "C:\PrefectServer\Flows"

# Service identification
nssm set PrefectWorker DisplayName "Prefect Worker - Process Pool"
nssm set PrefectWorker Description "Prefect worker executing flows from my-process-pool"

# Startup - delayed to ensure server starts first
nssm set PrefectWorker Start SERVICE_DELAYED_AUTO_START

# Dependencies - start after Prefect Server
nssm set PrefectWorker DependOnService PrefectServer

# Environment variables
nssm set PrefectWorker AppEnvironmentExtra `
    "PREFECT_API_URL=http://127.0.0.1:4200/api" `
    "PREFECT_HOME=C:\PrefectServer\data" `
    "PYTHONUNBUFFERED=1" `
    "PYTHONIOENCODING=UTF-8"

# Logging
nssm set PrefectWorker AppStdout "C:\PrefectServer\Logs\worker-stdout.log"
nssm set PrefectWorker AppStderr "C:\PrefectServer\Logs\worker-stderr.log"
nssm set PrefectWorker AppRotateFiles 1
nssm set PrefectWorker AppRotateOnline 1
nssm set PrefectWorker AppRotateBytes 10485760

# Recovery
nssm set PrefectWorker AppThrottle 5000
nssm set PrefectWorker AppExit Default Restart
nssm set PrefectWorker AppRestartDelay 15000

sc.exe failure PrefectWorker reset= 86400 actions= restart/15000/restart/30000/restart/60000
```

### Service management commands

```powershell
# Start services
nssm start PrefectServer
nssm start PrefectWorker

# Check status
nssm status PrefectServer
nssm status PrefectWorker

# View in Services console
services.msc

# Stop services
nssm stop PrefectWorker
nssm stop PrefectServer

# Restart
nssm restart PrefectServer

# Edit configuration (opens GUI)
nssm edit PrefectServer
```

---

## Phase 6: IIS reverse proxy with Windows Authentication

### Install IIS with required features

```powershell
# Install IIS with all required role services
Install-WindowsFeature -Name `
    Web-Server, `
    Web-WebServer, `
    Web-Common-Http, `
    Web-Static-Content, `
    Web-Default-Doc, `
    Web-Http-Errors, `
    Web-Health, `
    Web-Http-Logging, `
    Web-Security, `
    Web-Filtering, `
    Web-Windows-Auth, `
    Web-WebSockets, `
    Web-Mgmt-Tools, `
    Web-Mgmt-Console `
    -IncludeManagementTools

# Verify installation
Get-WindowsFeature -Name Web* | Where-Object Installed
```

### Install URL Rewrite and ARR modules

```powershell
# Install URL Rewrite (must be first)
msiexec /i "C:\PrefectOffline\rewrite_amd64.msi" /qn /norestart /l*v "C:\PrefectServer\Logs\urlrewrite_install.log"

# Wait for completion
Start-Sleep -Seconds 30

# Install Application Request Routing
msiexec /i "C:\PrefectOffline\requestRouter_amd64.msi" /qn /norestart /l*v "C:\PrefectServer\Logs\arr_install.log"

# Restart IIS to load modules
iisreset /restart

# Verify modules installed
Test-Path "$env:SystemRoot\System32\inetsrv\rewrite.dll"
Test-Path "$env:SystemRoot\System32\inetsrv\requestRouter.dll"
```

### Enable ARR proxy functionality

```powershell
# Enable ARR at server level
& "$env:SystemRoot\System32\inetsrv\appcmd.exe" set config -section:system.webServer/proxy /enabled:True /commit:apphost
& "$env:SystemRoot\System32\inetsrv\appcmd.exe" set config -section:system.webServer/proxy /preserveHostHeader:True /commit:apphost
& "$env:SystemRoot\System32\inetsrv\appcmd.exe" set config -section:system.webServer/proxy /reverseRewriteHostInResponseHeaders:False /commit:apphost
```

### Register allowed server variables for header forwarding

```powershell
Import-Module WebAdministration

# Add server variables that URL Rewrite can set
Add-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' `
    -filter "system.webServer/rewrite/allowedServerVariables" `
    -name "." -value @{name='HTTP_X_FORWARDED_PROTO'}

Add-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' `
    -filter "system.webServer/rewrite/allowedServerVariables" `
    -name "." -value @{name='HTTP_X_FORWARDED_HOST'}

Add-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' `
    -filter "system.webServer/rewrite/allowedServerVariables" `
    -name "." -value @{name='HTTP_X_FORWARDED_USER'}

Add-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' `
    -filter "system.webServer/rewrite/allowedServerVariables" `
    -name "." -value @{name='HTTP_X_FORWARDED_FOR'}
```

### Create the reverse proxy site

```powershell
Import-Module WebAdministration

$siteName = "PrefectProxy"
$sitePath = "C:\inetpub\PrefectProxy"
$hostHeader = "prefect.yourdomain.com"  # Change to your hostname

# Create site directory
New-Item -ItemType Directory -Path $sitePath -Force

# Create dedicated application pool (no managed code needed for reverse proxy)
New-WebAppPool -Name "${siteName}Pool"
Set-ItemProperty "IIS:\AppPools\${siteName}Pool" -Name "managedRuntimeVersion" -Value ""
Set-ItemProperty "IIS:\AppPools\${siteName}Pool" -Name "processModel.idleTimeout" -Value "00:00:00"

# Remove default site if desired
# Remove-Website -Name "Default Web Site"

# Create the Prefect proxy site (initially on port 80)
New-Website -Name $siteName `
    -PhysicalPath $sitePath `
    -HostHeader $hostHeader `
    -Port 80 `
    -ApplicationPool "${siteName}Pool"
```

### Create the web.config with reverse proxy rules

Create the file `C:\inetpub\PrefectProxy\web.config`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <!-- URL Rewrite Rules -->
        <rewrite>
            <rules>
                <!-- Redirect HTTP to HTTPS -->
                <rule name="HTTPS Redirect" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTPS}" pattern="^OFF$" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
                </rule>
                
                <!-- WebSocket connections -->
                <rule name="WebSocketProxy" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTP_UPGRADE}" pattern="websocket" />
                    </conditions>
                    <action type="Rewrite" url="http://127.0.0.1:4200/{R:1}" />
                </rule>
                
                <!-- Main reverse proxy rule -->
                <rule name="ReverseProxyToPrefect" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:4200/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="https" />
                        <set name="HTTP_X_FORWARDED_HOST" value="{HTTP_HOST}" />
                        <set name="HTTP_X_FORWARDED_USER" value="{LOGON_USER}" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        
        <!-- Security settings -->
        <security>
            <requestFiltering allowDoubleEscaping="true">
                <requestLimits maxAllowedContentLength="4294967295" maxUrl="1048576" maxQueryString="1048576" />
            </requestFiltering>
        </security>
        
        <!-- WebSocket support -->
        <webSocket enabled="true" />
    </system.webServer>
</configuration>
```

Save this content using PowerShell:

```powershell
$webConfig = @'
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="HTTPS Redirect" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTPS}" pattern="^OFF$" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
                </rule>
                <rule name="WebSocketProxy" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTP_UPGRADE}" pattern="websocket" />
                    </conditions>
                    <action type="Rewrite" url="http://127.0.0.1:4200/{R:1}" />
                </rule>
                <rule name="ReverseProxyToPrefect" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:4200/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="https" />
                        <set name="HTTP_X_FORWARDED_HOST" value="{HTTP_HOST}" />
                        <set name="HTTP_X_FORWARDED_USER" value="{LOGON_USER}" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        <security>
            <requestFiltering allowDoubleEscaping="true">
                <requestLimits maxAllowedContentLength="4294967295" />
            </requestFiltering>
        </security>
        <webSocket enabled="true" />
    </system.webServer>
</configuration>
'@

$webConfig | Out-File -FilePath "C:\inetpub\PrefectProxy\web.config" -Encoding UTF8
```

### Enable Windows Authentication

```powershell
$siteName = "PrefectProxy"

# Disable Anonymous Authentication
Set-WebConfigurationProperty -Filter "/system.webServer/security/authentication/anonymousAuthentication" `
    -Name "enabled" -Value "False" -PSPath "IIS:\Sites\$siteName"

# Enable Windows Authentication
Set-WebConfigurationProperty -Filter "/system.webServer/security/authentication/windowsAuthentication" `
    -Name "enabled" -Value "True" -PSPath "IIS:\Sites\$siteName"

# Verify settings
Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/windowsAuthentication" `
    -Name "enabled" -PSPath "IIS:\Sites\$siteName"
```

### Configure SSL binding with existing certificate

```powershell
$siteName = "PrefectProxy"
$hostHeader = "prefect.yourdomain.com"

# Find your certificate thumbprint
Get-ChildItem -Path Cert:\LocalMachine\My | Format-Table Subject, Thumbprint, NotAfter

# Set the thumbprint of your SSL certificate
$thumbprint = "YOUR_CERTIFICATE_THUMBPRINT_HERE"

# Create HTTPS binding
New-WebBinding -Name $siteName -Protocol "https" -Port 443 -HostHeader $hostHeader -SslFlags 1

# Bind the certificate
$binding = Get-WebBinding -Name $siteName -Protocol "https"
$binding.AddSslCertificate($thumbprint, "My")

# Optionally remove HTTP binding after confirming HTTPS works
# Remove-WebBinding -Name $siteName -Protocol "http" -Port 80

# Verify bindings
Get-WebBinding -Name $siteName
```

---

## Phase 7: Firewall configuration for security

### Block external access to Prefect port 4200

Since IIS proxies all requests, the Prefect server should only accept connections from localhost.

```powershell
# Block ALL external access to port 4200
New-NetFirewallRule -DisplayName "Block Prefect Port 4200 - External" `
    -Direction Inbound `
    -LocalPort 4200 `
    -Protocol TCP `
    -Action Block `
    -Profile Any

# Allow localhost access to port 4200 (IIS to Prefect)
New-NetFirewallRule -DisplayName "Allow Prefect Port 4200 - Localhost" `
    -Direction Inbound `
    -LocalPort 4200 `
    -Protocol TCP `
    -Action Allow `
    -RemoteAddress "127.0.0.1" `
    -Profile Any

# Note: Allow rule for localhost takes precedence over block rule
```

### Allow IIS web traffic

```powershell
# Allow HTTPS (required)
New-NetFirewallRule -DisplayName "IIS HTTPS Inbound" `
    -Direction Inbound `
    -LocalPort 443 `
    -Protocol TCP `
    -Action Allow `
    -Profile @('Domain', 'Private')

# Allow HTTP only if needed for redirect (optional)
New-NetFirewallRule -DisplayName "IIS HTTP Inbound" `
    -Direction Inbound `
    -LocalPort 80 `
    -Protocol TCP `
    -Action Allow `
    -Profile @('Domain', 'Private')
```

### Verify firewall rules

```powershell
# List all Prefect-related rules
Get-NetFirewallRule -DisplayName "*Prefect*" | Format-Table Name, DisplayName, Action, Enabled

# List all IIS-related rules
Get-NetFirewallRule -DisplayName "*IIS*" | Format-Table Name, DisplayName, Action, Enabled

# Test port accessibility from another machine
# Should FAIL for port 4200, SUCCEED for port 443
Test-NetConnection -ComputerName prefect.yourdomain.com -Port 4200
Test-NetConnection -ComputerName prefect.yourdomain.com -Port 443
```

---

## Phase 8: Verification and testing

### Test Prefect API endpoints

```powershell
# Health check (shallow)
Invoke-WebRequest -Uri "http://localhost:4200/api/health" -Method GET
# Expected: StatusCode 200, Content: true

# Ready check (includes database)
Invoke-WebRequest -Uri "http://localhost:4200/api/ready" -Method GET
# Expected: StatusCode 200

# Hello endpoint
Invoke-WebRequest -Uri "http://localhost:4200/api/hello" -Method GET
# Expected: Content: 👋

# Version
Invoke-WebRequest -Uri "http://localhost:4200/api/version" -Method GET
```

### Test IIS reverse proxy

```powershell
# Test via IIS (from another machine or using FQDN)
Invoke-WebRequest -Uri "https://prefect.yourdomain.com/api/health" -UseDefaultCredentials
# Expected: StatusCode 200 after Windows Authentication

# Check forwarded user header is working
# (Requires checking Prefect server logs or custom endpoint)
```

### Test Windows Authentication is enforced

```powershell
# This should FAIL without credentials
Invoke-WebRequest -Uri "https://prefect.yourdomain.com/api/health"
# Expected: 401 Unauthorized

# This should SUCCEED with Windows credentials
Invoke-WebRequest -Uri "https://prefect.yourdomain.com/api/health" -UseDefaultCredentials
# Expected: 200 OK
```

### Deploy and run a sample test workflow

Create the file `C:\PrefectServer\Flows\test_flow.py`:

```python
from prefect import flow, task
from datetime import datetime
import platform

@task
def get_system_info() -> dict:
    """Gather system information."""
    info = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "timestamp": datetime.now().isoformat()
    }
    print(f"System: {info['platform']}")
    return info

@task
def calculate_sum(numbers: list) -> int:
    """Calculate sum of numbers."""
    result = sum(numbers)
    print(f"Sum of {numbers} = {result}")
    return result

@flow(name="test-deployment-flow", log_prints=True)
def test_flow(name: str = "Windows Server", numbers: list = None):
    """Test flow for validating Prefect deployment."""
    if numbers is None:
        numbers = [1, 2, 3, 4, 5]
    
    print(f"Hello, {name}! Starting test flow...")
    
    system_info = get_system_info()
    total = calculate_sum(numbers)
    
    result = {
        "greeting": f"Hello, {name}!",
        "system": system_info,
        "calculation": total
    }
    
    print(f"Flow completed successfully!")
    return result


if __name__ == "__main__":
    # For testing: run directly
    result = test_flow("Test User")
    print(f"Result: {result}")
```

### Run the test flow locally

```powershell
# Activate environment
C:\PrefectServer\venv\Scripts\activate

# Run flow directly
python C:\PrefectServer\Flows\test_flow.py
```

### Deploy flow to work pool

```powershell
# Activate environment
C:\PrefectServer\venv\Scripts\activate
cd C:\PrefectServer\Flows

# Deploy the flow
python -c "
from test_flow import test_flow
test_flow.deploy(
    name='test-deployment',
    work_pool_name='my-process-pool',
    tags=['windows', 'test']
)
"

# Trigger a flow run
prefect deployment run "test-deployment-flow/test-deployment" --param name="Production Test"

# Check flow runs
prefect flow-run ls
```

### Access the Prefect UI

Open a browser and navigate to `https://prefect.yourdomain.com`. After Windows Authentication, you should see:

- **Dashboard** with flow run overview
- **Flows** tab listing deployed flows
- **Deployments** showing test-deployment
- **Work Pools** showing my-process-pool with active worker

---

## Troubleshooting common issues

### Service fails to start

```powershell
# Check NSSM service status
nssm status PrefectServer

# View Windows Event Log
Get-EventLog -LogName Application -Source "PrefectServer" -Newest 10

# Check service log files
Get-Content "C:\PrefectServer\Logs\server-stderr.log" -Tail 50

# Test manual start
C:\PrefectServer\venv\Scripts\python.exe -m prefect server start
```

### Port 4200 already in use

```powershell
# Find process using port
netstat -ano | findstr :4200

# Get process details
Get-Process -Id <PID>

# Kill if necessary
Stop-Process -Id <PID> -Force

# Or use alternate port
nssm set PrefectServer AppParameters "-m prefect server start --host 127.0.0.1 --port 4201"
```

### SQLite database lock errors

SQLite doesn't handle high concurrency well. If you see database lock errors:

```powershell
# Stop all Prefect services
nssm stop PrefectWorker
nssm stop PrefectServer

# Reset database (CAUTION: loses all data)
Remove-Item "C:\PrefectServer\data\prefect.db" -Force

# Restart services
nssm start PrefectServer
Start-Sleep 15
nssm start PrefectWorker

# For production, migrate to PostgreSQL
```

### Worker can't connect to server

```powershell
# Verify PREFECT_API_URL is set correctly
nssm get PrefectWorker AppEnvironmentExtra

# Test API connectivity
Invoke-WebRequest -Uri "http://127.0.0.1:4200/api/health"

# Check worker logs
Get-Content "C:\PrefectServer\Logs\worker-stderr.log" -Tail 50

# Ensure server started before worker
nssm restart PrefectServer
Start-Sleep 20
nssm restart PrefectWorker
```

### IIS returns 502 Bad Gateway

```powershell
# Check if Prefect server is running
Invoke-WebRequest -Uri "http://127.0.0.1:4200/api/health"

# Verify ARR is enabled
& "$env:SystemRoot\System32\inetsrv\appcmd.exe" list config -section:system.webServer/proxy

# Check URL Rewrite module
Get-WebGlobalModule | Where-Object {$_.Name -like "*Rewrite*"}

# Review IIS logs
Get-Content "C:\inetpub\logs\LogFiles\W3SVC*\*.log" -Tail 20
```

### Windows Authentication not working

```powershell
# Verify authentication settings
Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/windowsAuthentication" `
    -Name "enabled" -PSPath "IIS:\Sites\PrefectProxy"

# Should return True
Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/anonymousAuthentication" `
    -Name "enabled" -PSPath "IIS:\Sites\PrefectProxy"

# Should return False

# If issues persist, check the SPN registration for Kerberos
setspn -L computername
```

---

## Conclusion

This deployment establishes a production-ready Prefect 3.x environment on an air-gapped Windows Server 2019. The architecture provides **enterprise security** through IIS Windows Authentication, **reliability** through NSSM service management with automatic recovery, and **isolation** through firewall rules blocking direct Prefect API access.

Key architectural decisions include binding Prefect to localhost only (127.0.0.1), using IIS as the sole entry point with Windows Authentication, and configuring NSSM services with proper dependencies so the worker starts only after the server is ready. For scaling beyond SQLite's limitations, plan a PostgreSQL migration—the only production database Prefect supports besides SQLite.

The `X-FORWARDED-USER` header passes the authenticated Windows username to Prefect, enabling future integration with Prefect's RBAC features if you connect to Prefect Cloud or implement custom authorization logic.