$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$log = Join-Path $PSScriptRoot "setup_windows.log"

function Log($message) {
    $line = "$(Get-Date -Format o) $message"
    Add-Content -Path $log -Value $line
    Write-Host $message
}

try {
    Log "Starting Alpha Velocity setup."

    $pyCommand = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pyCommand = "py"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pyCommand = "python"
    } else {
        throw "Python was not found. Install Python 3.11+ and enable Add Python to PATH."
    }

    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Log "Creating permanent virtual environment."
        if ($pyCommand -eq "py") {
            & py -3 -m venv .venv
        } else {
            & python -m venv .venv
        }
    } else {
        Log "Reusing permanent virtual environment."
    }

    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
    & $python -m pip install -e .

    $ibkrPath = "C:\TWS API\source\pythonclient"
    & $python -c "import ibapi" 2>$null
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path $ibkrPath) {
            Log "Installing official IBKR API."
            & $python -m pip install $ibkrPath
        } else {
            Log "WARNING: Official IBKR API not found at $ibkrPath."
        }
    }

    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Automated tests failed."
    }

    if (-not (Test-Path "config.yaml") -and (Test-Path "config.example.yaml")) {
        Copy-Item config.example.yaml config.yaml
    }

    Log "SETUP COMPLETE."
} catch {
    Log "SETUP FAILED: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Log file: $log"
Read-Host "Press Enter to close"
