$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Alpha Velocity Persistent Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Find-Python {
    $candidates = @(
        @("py", "-3.11"),
        @("py", "-3"),
        @("python", "")
    )
    foreach ($candidate in $candidates) {
        try {
            if ($candidate[1] -eq "") {
                & $candidate[0] --version 2>$null
            } else {
                & $candidate[0] $candidate[1] --version 2>$null
            }
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {}
    }
    throw "Python 3.11 or newer was not found. Install Python and check Add Python to PATH."
}

$python = Find-Python

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[1/7] Creating the permanent virtual environment..." -ForegroundColor Yellow
    if ($python[1] -eq "") {
        & $python[0] -m venv .venv
    } else {
        & $python[0] $python[1] -m venv .venv
    }
} else {
    Write-Host "[1/7] Reusing the existing permanent virtual environment." -ForegroundColor Green
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

Write-Host "[2/7] Updating pip..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip

Write-Host "[3/7] Installing Alpha Velocity in editable mode..." -ForegroundColor Yellow
& $venvPython -m pip install -e .

Write-Host "[4/7] Installing test tools..." -ForegroundColor Yellow
& $venvPython -m pip install pytest

Write-Host "[5/7] Checking the official IBKR Python API..." -ForegroundColor Yellow
& $venvPython -c "import ibapi; print('IBKR API already installed:', getattr(ibapi, '__version__', 'unknown'))" 2>$null
if ($LASTEXITCODE -ne 0) {
    $ibkrPaths = @(
        "C:\TWS API\source\pythonclient",
        "C:\IB_API\source\pythonclient"
    )
    $installed = $false
    foreach ($path in $ibkrPaths) {
        if (Test-Path $path) {
            Write-Host "Found official IBKR API at $path" -ForegroundColor Green
            & $venvPython -m pip install $path
            $installed = $true
            break
        }
    }
    if (-not $installed) {
        Write-Host ""
        Write-Host "The official IBKR API was not found automatically." -ForegroundColor Red
        Write-Host "Install the TWS API to C:\TWS API, then run this installer again." -ForegroundColor Yellow
        Write-Host "The rest of Alpha Velocity has still been installed." -ForegroundColor Yellow
    }
}

Write-Host "[6/7] Running all tests..." -ForegroundColor Yellow
& $venvPython -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed. Do not connect to IBKR until the failure is reviewed."
}

Write-Host "[7/7] Verifying configuration..." -ForegroundColor Yellow
if (-not (Test-Path "config.yaml")) {
    Copy-Item "config.example.yaml" "config.yaml"
    Write-Host "Created config.yaml from the safe example." -ForegroundColor Green
} else {
    Write-Host "Existing config.yaml was preserved." -ForegroundColor Green
}

Write-Host ""
Write-Host "INSTALLATION COMPLETE" -ForegroundColor Green
Write-Host "This folder and its .venv are now permanent." -ForegroundColor Green
Write-Host "Future updates should replace code files only, not this folder." -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to close"
