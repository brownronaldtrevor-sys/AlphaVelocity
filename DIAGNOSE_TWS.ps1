$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host "Alpha Velocity TWS Diagnostic" -ForegroundColor Cyan
Write-Host ""

$python = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "FAIL: Permanent virtual environment is missing." -ForegroundColor Red
    Write-Host "Run INSTALL_OR_REPAIR.bat first."
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "1. Python environment" -ForegroundColor Yellow
& $python --version

Write-Host ""
Write-Host "2. Alpha Velocity import" -ForegroundColor Yellow
& $python -c "import alpha_velocity; print('OK:', alpha_velocity.__version__)"

Write-Host ""
Write-Host "3. Official IBKR API import" -ForegroundColor Yellow
& $python -c "import ibapi; print('OK:', getattr(ibapi, '__version__', 'unknown'))"

Write-Host ""
Write-Host "4. TWS paper socket 7497" -ForegroundColor Yellow
$test = Test-NetConnection 127.0.0.1 -Port 7497 -WarningAction SilentlyContinue
Write-Host "TcpTestSucceeded:" $test.TcpTestSucceeded

Write-Host ""
Write-Host "5. Safe configuration" -ForegroundColor Yellow
Get-Content .\config.yaml | Select-String "mode:|dry_run:|port:"

Write-Host ""
if ($test.TcpTestSucceeded) {
    Write-Host "Socket is open. TWS appears reachable." -ForegroundColor Green
} else {
    Write-Host "Socket is closed. Open TWS Paper and confirm API port 7497." -ForegroundColor Red
}
Read-Host "Press Enter to close"
