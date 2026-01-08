param (
    [Parameter(Mandatory=$true)]
    [string]$ConfigPath
)

if (-not (Test-Path $ConfigPath)) {
    Write-Error "File not found: $ConfigPath"
    exit 1
}

try {
    [xml]$xml = Get-Content $ConfigPath -ErrorAction Stop
}
catch {
    Write-Error "Invalid XML: $($_.Exception.Message)"
    exit 1
}

$service = $xml.service
if (-not $service) {
    Write-Error "Missing root <service> element."
    exit 1
}

$errors = @()

if (-not $service.id) {
    $errors += "Missing <id> element."
}
if (-not $service.executable) {
    $errors += "Missing <executable> element."
}

if ($errors.Count -gt 0) {
    Write-Error "Configuration validation failed:`n$($errors -join "`n")"
    exit 1
}

Write-Host "Configuration '$ConfigPath' is valid." -ForegroundColor Green
exit 0
