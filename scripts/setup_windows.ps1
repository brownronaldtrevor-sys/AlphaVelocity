$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Alpha Velocity Windows Setup" -ForegroundColor Cyan
Write-Host " Project folder: $Root"
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.11+ and select 'Add Python to PATH'."
}

$PythonLauncher = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    & $PythonLauncher -m venv .venv
}

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment creation failed."
}

Write-Host "Upgrading pip..."
& $VenvPython -m pip install --upgrade pip

Write-Host "Installing Alpha Velocity and test tools..."
& $VenvPython -m pip install -e ".[dev]"

if (-not (Test-Path "config.yaml")) {
    Copy-Item "config.example.yaml" "config.yaml"
    Write-Host "Created config.yaml from the safe paper template."
}

$IbapiInstalled = $false
& $VenvPython -c "import ibapi" 2>$null
if ($LASTEXITCODE -eq 0) { $IbapiInstalled = $true }

if (-not $IbapiInstalled) {
    $Candidates = @(
        "C:\TWS API\source\pythonclient",
        "C:\TWS API\source\pythonclient\dist",
        "$env:USERPROFILE\TWS API\source\pythonclient"
    )
    $PythonClient = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($PythonClient) {
        Write-Host "Installing official IBKR Python API from: $PythonClient"
        & $VenvPython -m pip install $PythonClient
    } else {
        Write-Warning "Official IBKR API was not found automatically."
        Write-Warning "Install TWS API, then run:"
        Write-Warning '  .\.venv\Scripts\python.exe -m pip install "C:\TWS API\source\pythonclient"'
    }
}

Write-Host "Running test suite..."
& $VenvPython -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed. Stop and review the output."
}

Write-Host "Running readiness diagnostics..."
& $VenvPython scripts\diagnose.py

Write-Host ""
Write-Host "SETUP COMPLETE." -ForegroundColor Green
Write-Host "Next: open TWS Paper, enable API socket clients, keep Read-Only ON, then double-click CONNECT_TWS_READ_ONLY.bat"
