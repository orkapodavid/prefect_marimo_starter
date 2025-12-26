<#
.SYNOPSIS
    Installs and configures IIS as a Reverse Proxy for Prefect.
    
.PARAMETER OfflineSource
    Path to downloaded assets (module MSIs). Defaults to "C:\PrefectOffline".
    
.PARAMETER HostName
    The DNS hostname for the Prefect server (e.g., prefect.corp.local).
    Defaults to "localhost" (for testing, but real deployment should change this).
    
.PARAMETER Thumbprint
    SSL Certificate Thumbprint. If provided, sets up HTTPS.
#>

param(
    [string]$OfflineSource = "C:\PrefectOffline",
    [string]$HostName = "prefect.local",
    [string]$Thumbprint = ""
)

$ErrorActionPreference = "Stop"

# 1. Install IIS Features
Write-Host "Installing IIS Features..." -ForegroundColor Cyan
try {
    Install-WindowsFeature -Name `
        Web-Server, Web-WebServer, Web-Common-Http, Web-Static-Content, `
        Web-Default-Doc, Web-Http-Errors, Web-Health, Web-Http-Logging, `
        Web-Security, Web-Filtering, Web-Windows-Auth, Web-WebSockets, `
        Web-Mgmt-Tools, Web-Mgmt-Console `
        -IncludeManagementTools | Out-Null
} catch {
    Write-Host "Could not run Install-WindowsFeature. Ensure you are on Windows Server and running as Admin." -ForegroundColor Red
    # Continue only if on non-server Windows for testing (optional logic, but typically we stop)
    # exit 1
}

# 2. Install Modules
$RewriteMsi = "$OfflineSource\rewrite_amd64.msi"
$ArrMsi = "$OfflineSource\requestRouter_amd64.msi"

if (-not (Test-Path "$env:SystemRoot\System32\inetsrv\rewrite.dll")) {
    Write-Host "Installing URL Rewrite..." -ForegroundColor Cyan
    Start-Process msiexec.exe -ArgumentList "/i `"$RewriteMsi`" /qn /norestart" -Wait
}

if (-not (Test-Path "$env:SystemRoot\System32\inetsrv\requestRouter.dll")) {
    Write-Host "Installing ARR..." -ForegroundColor Cyan
    Start-Process msiexec.exe -ArgumentList "/i `"$ArrMsi`" /qn /norestart" -Wait
}

# 3. Enable ARR Proxy
Write-Host "Enabling ARR Proxy..." -ForegroundColor Cyan
$AppCmd = "$env:SystemRoot\System32\inetsrv\appcmd.exe"
& $AppCmd set config -section:system.webServer/proxy /enabled:True /commit:apphost
& $AppCmd set config -section:system.webServer/proxy /preserveHostHeader:True /commit:apphost
& $AppCmd set config -section:system.webServer/proxy /reverseRewriteHostInResponseHeaders:False /commit:apphost

# 4. Allow Server Variables
Write-Host "Configuring Allowed Server Variables..." -ForegroundColor Cyan
# PowerShell IIS module way
Import-Module WebAdministration
$Variables = @('HTTP_X_FORWARDED_PROTO', 'HTTP_X_FORWARDED_HOST', 'HTTP_X_FORWARDED_USER', 'HTTP_X_FORWARDED_FOR')
foreach ($var in $Variables) {
    Add-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' `
        -filter "system.webServer/rewrite/allowedServerVariables" `
        -name "." -value @{name=$var} -ErrorAction SilentlyContinue
}

# 5. Create Site
$SiteName = "PrefectProxy"
$SitePath = "C:\inetpub\PrefectProxy"

if (-not (Test-Path $SitePath)) {
    New-Item -ItemType Directory -Path $SitePath -Force | Out-Null
}

# Web.Config Content
$WebConfigContent = @'
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
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        <security>
            <requestFiltering allowDoubleEscaping="true">
                <requestLimits maxAllowedContentLength="4294967295" />
            </requestFiltering>
            <authentication>
                <anonymousAuthentication enabled="false" />
                <windowsAuthentication enabled="true" />
            </authentication>
        </security>
        <webSocket enabled="true" />
    </system.webServer>
</configuration>
'@

Set-Content -Path "$SitePath\web.config" -Value $WebConfigContent -Encoding UTF8

# Create App Pool & Site
if (Get-Website -Name $SiteName -ErrorAction SilentlyContinue) {
    Remove-Website -Name $SiteName
}

# Create AppPool if not exists
$PoolName = "${SiteName}Pool"
if (-not (Test-Path "IIS:\AppPools\$PoolName")) {
    New-WebAppPool -Name $PoolName
}
Set-ItemProperty "IIS:\AppPools\$PoolName" -Name "managedRuntimeVersion" -Value ""
Set-ItemProperty "IIS:\AppPools\$PoolName" -Name "processModel.idleTimeout" -Value "00:00:00"

# Create Website
Write-Host "Creating Website $SiteName..."
New-Website -Name $SiteName -PhysicalPath $SitePath -HostHeader $HostName -Port 80 -ApplicationPool $PoolName -Force

# SSL Setup (if thumbprint provided)
if ($Thumbprint) {
    Write-Host "Configuring SSL..." -ForegroundColor Cyan
    New-WebBinding -Name $SiteName -Protocol "https" -Port 443 -HostHeader $HostName -SslFlags 1
    $binding = Get-WebBinding -Name $SiteName -Protocol "https"
    $binding.AddSslCertificate($Thumbprint, "My")
    
    # Optional: Add HTTPS redirect rule to web.config if needed
    Write-Host "SSL Configured. Please ensure web.config has HTTPS redirect if desired."
}

Write-Host "=== IIS Setup Complete ===" -ForegroundColor Green
Write-Host "URL: http://$HostName (or https if configured)"
