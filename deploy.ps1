# ChildStudy Server Deploy Script
# Usage: run in server PowerShell (Administrator)
#   cd C:\ChildStudy
#   .\deploy.ps1
#
# Prerequisite: copy the updated ChildStudy folder from local to C:\ChildStudy\
# Works for both first-time deploy and updates (auto-detects venv / node_modules / running process)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\ChildStudy"
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

function Write-Step($msg) {
    Write-Host ""
    Write-Host ">>> $msg" -ForegroundColor Cyan
}

# ---------- 0. sanity check ----------
Write-Step "Checking project layout"
if (-not (Test-Path (Join-Path $BackendDir "main.py"))) {
    Write-Host "ERROR: cannot find backend/main.py. Is C:\ChildStudy\ really the project root?" -ForegroundColor Red
    exit 1
}
Write-Host "Project root: $ProjectRoot" -ForegroundColor Green

# ---------- 1. backup database ----------
Write-Step "Backing up database (in case upgrade fails)"
$dbPath = Join-Path $BackendDir "data\childstudy.db"
if (Test-Path $dbPath) {
    $backupPath = "$dbPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $dbPath $backupPath
    Write-Host "Backed up to $backupPath" -ForegroundColor Green
} else {
    Write-Host "Database file not found (first deploy?)" -ForegroundColor Yellow
}

# ---------- 2. backend deps ----------
Write-Step "Upgrading backend deps (pip install -r requirements.txt)"
Set-Location $BackendDir
$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$venvPip = Join-Path $BackendDir ".venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "venv missing, creating..." -ForegroundColor Yellow
    python -m venv .venv
    & $venvPip install -r requirements.txt
} else {
    Write-Host "venv exists, incremental upgrade..." -ForegroundColor Green
    & $venvPip install -r requirements.txt
}

# ---------- 3. frontend build ----------
Write-Step "Building frontend (npm install + npm run build)"
Set-Location $FrontendDir
if (-not (Test-Path "node_modules")) {
    Write-Host "node_modules missing, npm install (slow on first run)..." -ForegroundColor Yellow
    npm install
} else {
    Write-Host "node_modules exists, incremental install..." -ForegroundColor Green
    npm install
}
Write-Host "Running npm run build..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed, aborting." -ForegroundColor Red
    exit 1
}

# ---------- 4. stop old process ----------
Write-Step "Restarting backend service"
$oldProcs = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%main.py%'" -ErrorAction SilentlyContinue
if ($oldProcs) {
    foreach ($p in $oldProcs) {
        Write-Host "Stopping old process PID $($p.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "No running main.py process detected (first deploy?)" -ForegroundColor Gray
}

# ---------- 5. start new ----------
Write-Step "Starting backend"
Set-Location $BackendDir
Start-Process -FilePath $venvPython -ArgumentList "main.py" -WorkingDirectory $BackendDir -WindowStyle Hidden
Start-Sleep -Seconds 3

$newProcs = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%main.py%'" -ErrorAction SilentlyContinue
if ($newProcs) {
    foreach ($p in $newProcs) {
        Write-Host "New process started PID $($p.ProcessId)" -ForegroundColor Green
    }
} else {
    Write-Host "WARNING: no main.py process detected after startup. Check logs." -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Deploy complete ===" -ForegroundColor Cyan
Write-Host "Access: http://127.0.0.1:8000  or your domain" -ForegroundColor Green
Write-Host "Logs:   see backend/ for runtime output" -ForegroundColor Gray
