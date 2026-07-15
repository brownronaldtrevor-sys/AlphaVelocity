param(
    [Parameter(Mandatory=$true)]
    [string]$UpdateZip
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "This is not an installed Alpha Velocity folder. Run INSTALL_OR_REPAIR.bat first."
}
if (-not (Test-Path $UpdateZip)) {
    throw "Update ZIP not found: $UpdateZip"
}

$backup = Join-Path $PSScriptRoot ("backup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$temp = Join-Path $env:TEMP ("AlphaVelocityUpdate_" + [guid]::NewGuid())

Write-Host "Backing up code and configuration to $backup" -ForegroundColor Yellow
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($item in @("alpha_velocity", "tests", "docs", "examples", "pyproject.toml", "README.md")) {
    if (Test-Path $item) { Copy-Item $item $backup -Recurse -Force }
}

Expand-Archive -Path $UpdateZip -DestinationPath $temp -Force
$source = Get-ChildItem $temp -Directory | Select-Object -First 1
if ($null -eq $source) { $source = Get-Item $temp }

Write-Host "Applying update while preserving .venv, config.yaml, reports, and logs..." -ForegroundColor Yellow
foreach ($item in @("alpha_velocity", "tests", "docs", "examples", "pyproject.toml", "README.md")) {
    $srcItem = Join-Path $source.FullName $item
    if (Test-Path $srcItem) {
        $dstItem = Join-Path $PSScriptRoot $item
        if (Test-Path $dstItem) { Remove-Item $dstItem -Recurse -Force }
        Copy-Item $srcItem $dstItem -Recurse -Force
    }
}

& ".\.venv\Scripts\python.exe" -m pip install -e .
& ".\.venv\Scripts\python.exe" -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Update tests failed. Backup is at $backup" -ForegroundColor Red
    throw "Update failed validation."
}

Remove-Item $temp -Recurse -Force
Write-Host "Update completed successfully." -ForegroundColor Green
Read-Host "Press Enter to close"
