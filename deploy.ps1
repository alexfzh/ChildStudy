# ChildStudy 服务器部署脚本
# 用法：在服务器 PowerShell（管理员）中执行
#   cd C:\ChildStudy
#   .\deploy.ps1
#
# 前置：先把本地更新后的整个 ChildStudy 文件夹复制到 C:\ChildStudy\ 覆盖
# 适用范围：首次部署 + 后续更新（自动检测 venv / node_modules / 主进程）

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\ChildStudy"
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

function Write-Step($msg) {
    Write-Host ""
    Write-Host ">>> $msg" -ForegroundColor Cyan
}

# ---------- 0. 基础检查 ----------
Write-Step "检查项目目录"
if (-not (Test-Path (Join-Path $BackendDir "main.py"))) {
    Write-Host "错误：找不到 backend/main.py，确认 C:\ChildStudy\ 是项目根目录" -ForegroundColor Red
    exit 1
}
Write-Host "项目根目录：$ProjectRoot" -ForegroundColor Green

# ---------- 1. 备份数据库 ----------
Write-Step "备份数据库（防升级翻车）"
$dbPath = Join-Path $BackendDir "data\childstudy.db"
if (Test-Path $dbPath) {
    $backupPath = "$dbPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $dbPath $backupPath
    Write-Host "已备份到 $backupPath" -ForegroundColor Green
} else {
    Write-Host "数据库文件不存在（首次部署？）" -ForegroundColor Yellow
}

# ---------- 2. 后端依赖 ----------
Write-Step "升级后端依赖（pip install -r requirements.txt）"
Set-Location $BackendDir
$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$venvPip = Join-Path $BackendDir ".venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "venv 不存在，创建中..." -ForegroundColor Yellow
    python -m venv .venv
    & $venvPip install -r requirements.txt
} else {
    Write-Host "venv 已存在，增量升级依赖..." -ForegroundColor Green
    & $venvPip install -r requirements.txt
}

# ---------- 3. 前端构建 ----------
Write-Step "构建前端（npm install + npm run build）"
Set-Location $FrontendDir
if (-not (Test-Path "node_modules")) {
    Write-Host "node_modules 不存在，npm install（首次较慢）..." -ForegroundColor Yellow
    npm install
} else {
    Write-Host "node_modules 已存在，增量安装..." -ForegroundColor Green
    npm install
}
Write-Host "执行 npm run build..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "前端构建失败，停止部署" -ForegroundColor Red
    exit 1
}

# ---------- 4. 杀掉旧进程 ----------
Write-Step "重启后端服务"
$oldProcs = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%main.py%'" -ErrorAction SilentlyContinue
if ($oldProcs) {
    foreach ($p in $oldProcs) {
        Write-Host "停止旧进程 PID $($p.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "未检测到运行中的 main.py 进程（首次部署？）" -ForegroundColor Gray
}

# ---------- 5. 启动 ----------
Write-Step "启动后端"
Set-Location $BackendDir
Start-Process -FilePath $venvPython -ArgumentList "main.py" -WorkingDirectory $BackendDir -WindowStyle Hidden
Start-Sleep -Seconds 3

$newProcs = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%main.py%'" -ErrorAction SilentlyContinue
if ($newProcs) {
    foreach ($p in $newProcs) {
        Write-Host "新进程已启动 PID $($p.ProcessId)" -ForegroundColor Green
    }
} else {
    Write-Host "警告：启动后未检测到 main.py 进程，请检查日志" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Cyan
Write-Host "访问：http://127.0.0.1:8000  或你的域名" -ForegroundColor Green
Write-Host "日志：查看 backend/ 下的运行输出" -ForegroundColor Gray
