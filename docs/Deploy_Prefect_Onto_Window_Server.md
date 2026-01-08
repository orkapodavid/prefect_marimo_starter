# Deploying Prefect 3.x on Air-Gapped Windows Server 2019

Prefect 3.x can be successfully deployed on an offline Windows Server 2019 environment using pre-downloaded packages, WinSW (Windows Service Wrapper) for service management, and IIS as a secure reverse proxy with Windows Authentication. This guide provides complete step-by-step instructions for the entire deployment process, from Python installation through verification testing.

The deployment requires **Python 3.12**, approximately **80-100 wheel files** for offline installation (including project-specific dependencies like `pyodbc` and `marimo`), and uses SQLite by default.

---

## Phase 1: Pre-download all required files on an internet-connected machine

Before transferring to your air-gapped server, you must gather all necessary installers and packages.

### Automated Download (Recommended)

Run the included script from the project root on a machine with internet access:

```powershell
.\scripts\windows\01_download_offline_assets.ps1 -Destination "C:\PrefectOffline"
```

This script will:
1. Download the Python 3.12 installer.
2. Download WinSW (Service Wrapper).
3. Download IIS Rewrite and ARR modules.
4. Download all Python wheels defined in `pyproject.toml` (Prefect, Marimo, PyODBC, etc.).
5. Bundle the application source code into `C:\PrefectOffline\app`.

### Manual Download (Alternative)

If you cannot run the script, manually download the following to `C:\PrefectOffline`:

1.  **Python 3.12.4 Installer (amd64)** from python.org.
2.  **WinSW** x64 executable (rename to `winsw.exe`) from the WinSW releases page (e.g., v2.12.0).
3.  **IIS URL Rewrite Module 2.0 (x64)** from Microsoft.
4.  **Application Request Routing 3.0 (x64)** from Microsoft.
5.  **Python Wheels**:
    ```powershell
    mkdir C:\PrefectOffline\wheels
    pip download . --dest C:\PrefectOffline\wheels --platform win_amd64 --python-version 3.12 --only-binary=:all:
    ```

### Transfer to air-gapped server

Copy the entire `C:\PrefectOffline` directory to removable media and transfer to the target server.

---

## Phase 2: Installation on the air-gapped server

You can automate this phase using the provided scripts or follow the manual steps below.

### Option A: Automated Installation (Fast)

Run these scripts in order as Administrator:

1.  **Install Environment**:
    ```powershell
    .\scripts\windows\02_install_server_env.ps1 -OfflineSource "C:\PrefectOffline" -InstallDir "C:\PrefectServer"
    ```

2.  **Configure Services**:
    ```powershell
    .\scripts\windows\03_configure_services.ps1 -OfflineSource "C:\PrefectOffline" -InstallDir "C:\PrefectServer"
    ```

3.  **Setup IIS Proxy**:
    ```powershell
    .\scripts\windows\04_setup_iis_proxy.ps1 -OfflineSource "C:\PrefectOffline" -HostName "prefect.corp.local"
    ```

### Option B: Manual Installation (Detailed)

Follow these steps if you need custom configuration or cannot use the scripts.

#### 1. Install Python

```powershell
Start-Process -Wait -FilePath "C:\PrefectOffline\python-3.12.4-amd64.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 TargetDir=C:\Python312"
```

#### 2. Install Packages

```powershell
# Create venv
C:\Python312\python.exe -m venv C:\PrefectServer\venv
C:\PrefectServer\venv\Scripts\activate

# Install from local wheels (Project + Prefect)
# Point to the bundled app directory to install the project itself
pip install --no-index --find-links=C:\PrefectOffline\wheels C:\PrefectOffline\app
```

#### 3. Database Configuration

Prefect uses SQLite by default at `%PREFECT_HOME%\prefect.db`. No extra setup required.

#### 4. Configure Services (WinSW)

Move the downloaded `winsw.exe` to your installation directory (e.g., `C:\PrefectServer`). You will make two copies of this executable: one for the server and one for the worker, and create a corresponding XML configuration file for each.

**A. Prefect Server Service:**

1. Copy `winsw.exe` to `C:\PrefectServer\PrefectServer.exe`.
2. Create `C:\PrefectServer\PrefectServer.xml` with the following content:

```xml
<service>
  <id>PrefectServer</id>
  <name>Prefect Orchestration Server</name>
  <description>Prefect 3.x workflow orchestration server</description>
  <executable>venv\Scripts\python.exe</executable>
  <arguments>-m prefect server start --host 127.0.0.1 --port 4200</arguments>
  <workingdirectory>%BASE%</workingdirectory>
  <env name="PREFECT_HOME" value="%BASE%\data"/>
  <env name="PREFECT_SERVER_API_HOST" value="127.0.0.1"/>
  <env name="PREFECT_SERVER_API_PORT" value="4200"/>
  <env name="PYTHONUNBUFFERED" value="1"/>
  <env name="PYTHONIOENCODING" value="UTF-8"/>
  <log mode="roll-by-size">
    <directory>%BASE%\Logs</directory>
    <sizeThreshold>10240</sizeThreshold> <!-- 10MB -->
    <keepFiles>1</keepFiles>
  </log>
  <onfailure action="restart" delay="10 sec"/>
</service>
```

3. Install and Start:
```powershell
Cd C:\PrefectServer
.\PrefectServer.exe install
.\PrefectServer.exe start
```

**B. Prefect Worker Service:**

1. Copy `winsw.exe` to `C:\PrefectServer\PrefectWorker.exe`.
2. Create `C:\PrefectServer\PrefectWorker.xml`:

```xml
<service>
  <id>PrefectWorker</id>
  <name>Prefect Worker - Process Pool</name>
  <description>Prefect Worker for Process Pool</description>
  <executable>venv\Scripts\python.exe</executable>
  <!-- Update pool name if different -->
  <arguments>-m prefect worker start --pool my-process-pool --type process</arguments>
  <workingdirectory>%BASE%</workingdirectory>
  <depend>PrefectServer</depend>
  <env name="PREFECT_API_URL" value="http://127.0.0.1:4200/api"/>
  <env name="PREFECT_HOME" value="%BASE%\data"/>
  <env name="PYTHONUNBUFFERED" value="1"/>
  <env name="PYTHONIOENCODING" value="UTF-8"/>
  <log mode="roll-by-size">
    <directory>%BASE%\Logs</directory>
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>1</keepFiles>
  </log>
  <onfailure action="restart" delay="10 sec"/>
  <startmode>DelayedStart</startmode>
</service>
```

3. Install and Start:
```powershell
.\PrefectWorker.exe install
.\PrefectWorker.exe start
```

#### 5. IIS Configuration

1. Install `rewrite_amd64.msi` and `requestRouter_amd64.msi`.
2. Enable ARR Proxy in IIS Manager.
3. Create a Site "PrefectProxy" pointing to `C:\inetpub\PrefectProxy`.
4. Create `web.config` with the following content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
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
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        <security>
            <authentication>
                <anonymousAuthentication enabled="false" />
                <windowsAuthentication enabled="true" />
            </authentication>
        </security>
        <webSocket enabled="true" />
    </system.webServer>
</configuration>
```

---

## Phase 3: Verification

### Service Status

```powershell
Get-Service PrefectServer
Get-Service PrefectWorker
```

### Deploy and run a sample test workflow

Create `C:\PrefectServer\Flows\test_flow.py` to verify the worker is picking up jobs:

```python
from prefect import flow, task
import platform

@task
def get_system_info():
    print(f"System: {platform.platform()}")

@flow(name="test-deployment-flow", log_prints=True)
def test_flow():
    print("Starting test flow...")
    get_system_info()
    print("Flow completed successfully!")

if __name__ == "__main__":
    # Deploy to the work pool we created
    test_flow.deploy(
        name="test-deployment",
        work_pool_name="my-process-pool",
        tags=["windows", "test"]
    )
```

Run deployment:
```powershell
C:\PrefectServer\venv\Scripts\python.exe C:\PrefectServer\Flows\test_flow.py
prefect deployment run "test-deployment-flow/test-deployment"
```

### Access

Navigate to `http://prefect.corp.local` (or your configured hostname).
You should see the Prefect Dashboard and the executed flow run.
