# ChildStudy Local Packaging Script (generates deployment zip)
# Usage: run in local PowerShell
#   cd C:\Users\feizhonghua\.openclaw\workspace-musk\projects\ChildStudy
#   .\package.ps1
#
# Output: ChildStudy-update-yyyyMMdd-HHmmss.zip in project root
# Then upload this zip to Alibaba Cloud server C:\ChildStudy\ directory
# deploy.ps1 will handle the rest

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutputZip = Join-Path $ProjectRoot "ChildStudy-update-$timestamp.zip"

# Temp directory for staging files
$TempDir = Join-Path $env:TEMP "ChildStudy-pack-$timestamp"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    Write-Host "=== ChildStudy Local Packaging ===" -ForegroundColor Cyan
    Write-Host "Project root: $ProjectRoot" -ForegroundColor Green
    Write-Host "Staging: $TempDir" -ForegroundColor Green

    # ----- Step 1: mirror project with exclusions -----
    Write-Host ""
    Write-Host "[1/3] Copying files with exclusions..." -ForegroundColor Cyan

    $excludeDirs = @(
        ".venv"
        "__pycache__"
        ".pytest_cache"
        ".ruff_cache"
        "node_modules"
        "dist"
        ".git"
        ".idea"
        ".vscode"
        "data"
        "uploads"
        "reports"
    )

    $excludeFiles = @(
        "*.pyc"
        "*.pyo"
        "*.log"
        "*.bak"
        "*.tmp"
        "*.db-journal"
        "*.db-wal"
        "*.db-shm"
        "vite.config.js.timestamp-*"
        "dev.log"
        "frontend_run.log"
        ".env"
    )

    $xdArgs = @()
    foreach ($d in $excludeDirs) { $xdArgs += "/XD"; $xdArgs += $d }
    $xfArgs = @()
    foreach ($f in $excludeFiles) { $xfArgs += "/XF"; $xfArgs += $f }

    & robocopy "$ProjectRoot" "$TempDir" /MIR /NJH /NJS /NDL /NFL /NP @xdArgs @xfArgs | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }

    # ----- Step 2: cleanup leftover stubs -----
    Write-Host "[2/3] Cleaning up..." -ForegroundColor Cyan

    Get-ChildItem -Path $TempDir -Recurse -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @(".venv","__pycache__",".pytest_cache",".ruff_cache","node_modules","dist",".git","data","uploads","reports") } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    Get-ChildItem -Path $TempDir -Recurse -Include @("*.log","*.pyc","*.pyo","*.bak","*.tmp") -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue

    # ----- Step 3: compress to zip -----
    Write-Host "[3/3] Compressing to zip..." -ForegroundColor Cyan
    if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
    Compress-Archive -Path "$TempDir\*" -DestinationPath $OutputZip

    $size = (Get-Item $OutputZip).Length
    Write-Host ""
    Write-Host "=== Done ===" -ForegroundColor Cyan
    Write-Host "Output: $OutputZip" -ForegroundColor Green
    Write-Host ("Size: {0:N2} MB" -f ($size / 1MB)) -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Upload this zip to server C:\ChildStudy-update.zip" -ForegroundColor White
    Write-Host "  2. On server PowerShell (admin):" -ForegroundColor White
    Write-Host "       cd C:\ChildStudy" -ForegroundColor White
    Write-Host "       Expand-Archive -Path C:\ChildStudy-update.zip -DestinationPath C:\ChildStudy -Force" -ForegroundColor White
    Write-Host "       .\deploy.ps1" -ForegroundColor White
}
finally {
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
    }
}
