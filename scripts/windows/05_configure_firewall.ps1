<#
.SYNOPSIS
    Configures Windows Firewall for Prefect security.
    Blocks external access to port 4200 (direct API).
    Allows IIS traffic (80/443).
#>

$ErrorActionPreference = "Stop"

Write-Host "Configuring Firewall Rules..." -ForegroundColor Cyan

# 1. Block External Port 4200
New-NetFirewallRule -DisplayName "Block Prefect Port 4200 - External" `
    -Direction Inbound `
    -LocalPort 4200 `
    -Protocol TCP `
    -Action Block `
    -Profile Any `
    -ErrorAction SilentlyContinue

# 2. Allow Localhost Port 4200 (for IIS Proxy)
New-NetFirewallRule -DisplayName "Allow Prefect Port 4200 - Localhost" `
    -Direction Inbound `
    -LocalPort 4200 `
    -Protocol TCP `
    -Action Allow `
    -RemoteAddress "127.0.0.1" `
    -Profile Any `
    -ErrorAction SilentlyContinue

# 3. Allow IIS Ports
New-NetFirewallRule -DisplayName "IIS HTTPS Inbound" `
    -Direction Inbound `
    -LocalPort 443 `
    -Protocol TCP `
    -Action Allow `
    -Profile @('Domain', 'Private', 'Public') `
    -ErrorAction SilentlyContinue

New-NetFirewallRule -DisplayName "IIS HTTP Inbound" `
    -Direction Inbound `
    -LocalPort 80 `
    -Protocol TCP `
    -Action Allow `
    -Profile @('Domain', 'Private', 'Public') `
    -ErrorAction SilentlyContinue

Write-Host "=== Firewall Configured ===" -ForegroundColor Green
Get-NetFirewallRule -DisplayName "*Prefect*" | Format-Table Name, DisplayName, Action, Enabled
