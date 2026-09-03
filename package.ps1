# ChildStudy 本地打包脚本（生成部署用的 zip）
# 用法：在本地 PowerShell 中执行
#   cd C:\Users\feizhonghua\.openclaw\workspace-musk\projects\ChildStudy
#   .\package.ps1
#
# 输出：项目根目录的 ChildStudy-update-yyyyMMdd-HHmmss.zip
# 然后把这个 zip 上传到阿里云服务器 C:\ChildStudy\ 目录（不需要解压，deploy.ps1 会处理）

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutputZip = Join-Path $ProjectRoot "ChildStudy-update-$timestamp.zip"

# 临时目录（解压后用于打包，避免项目目录里产生临时文件）
$TempDir = Join-Path $env:TEMP "ChildStudy-pack-$timestamp"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    Write-Host "=== ChildStudy 本地打包脚本 ===" -ForegroundColor Cyan
    Write-Host "项目根目录：$ProjectRoot" -ForegroundColor Green
    Write-Host "临时目录：$TempDir" -ForegroundColor Green

    # ---------- 复制需要更新的文件 ----------
    Write-Host ""
    Write-Host "[1/3] 复制需要更新的文件..." -ForegroundColor Cyan

    $excludeDirs = @(
        '.venv', '__pycache__', '.pytest_cache', '.ruff_cache',
        'node_modules', 'dist', '.git', '.idea', '.vscode',
        'data', 'uploads', 'reports',  # 服务器运行时产物，不要打包
        'data\.gitkeep', 'uploads\.gitkeep',
    )
    $excludeFilePatterns = @(
        '*.pyc', '*.pyo', '*.log', '*.bak*',
        '*.db-journal', '*.db-wal', '*.db-shm',
        'vite.config.js.timestamp-*',
        'dev.log', 'frontend_run.log',
        '*.tmp', '*.bak',
    )

    # 用 robocopy 镜像，排除指定的目录和文件
    # /MIR 镜像（含子目录），/XD 排除目录，/XF 排除文件
    $robocopyArgs = @(
        "`"$ProjectRoot`"",
        "`"$TempDir`"",
        '/MIR',
        '/NJH', '/NJS', '/NDL', '/NFL', '/NP'  # 安静模式
    )
    foreach ($d in $excludeDirs) {
        $robocopyArgs += "/XD"
        $robocopyArgs += "`"$d`""
    }
    foreach ($f in $excludeFilePatterns) {
        $robocopyArgs += "/XF"
        $robocopyArgs += "`"$f`""
    }

    # 关键：env 文件不打包（服务器有自己配的 .env，含 JWT secret 等敏感值）
    $robocopyArgs += '/XF'
    $robocopyArgs += '".env"'

    & robocopy @robocopyArgs | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy 失败，exit code: $LASTEXITCODE"
    }

    # ---------- 删除空目录 / 不必要的目录 ----------
    Write-Host "[2/3] 清理不需要的文件..." -ForegroundColor Cyan

    Get-ChildItem -Path $TempDir -Recurse -Directory | Where-Object {
        $_.Name -in @('.venv', '__pycache__', '.pytest_cache', '.ruff_cache',
                      'node_modules', 'dist', '.git', 'data', 'uploads', 'reports')
    } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    # 删除日志 / 临时文件
    Get-ChildItem -Path $TempDir -Recurse -Include ('*.log','*.pyc','*.pyo','*.bak*','*.tmp') |
        Remove-Item -Force -ErrorAction SilentlyContinue

    # 删除 env 文件（避免覆盖服务器上的敏感配置）
    Get-ChildItem -Path $TempDir -Recurse -Filter '.env' -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue

    # ---------- 打包 ----------
    Write-Host "[3/3] 压缩为 zip..." -ForegroundColor Cyan
    if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
    Compress-Archive -Path "$TempDir\*" -DestinationPath $OutputZip

    $size = (Get-Item $OutputZip).Length
    Write-Host ""
    Write-Host "=== 打包完成 ===" -ForegroundColor Cyan
    Write-Host "输出文件：$OutputZip" -ForegroundColor Green
    Write-Host "文件大小：$([math]::Round($size / 1MB, 2)) MB" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步：" -ForegroundColor Yellow
    Write-Host "  1. 把这个 zip 上传到服务器 C:\ChildStudy-update.zip" -ForegroundColor White
    Write-Host "  2. 在服务器 PowerShell（管理员）中执行：" -ForegroundColor White
    Write-Host "       cd C:\ChildStudy" -ForegroundColor White
    Write-Host "       Expand-Archive -Path C:\ChildStudy-update.zip -DestinationPath C:\ChildStudy -Force" -ForegroundColor White
    Write-Host "       .\deploy.ps1" -ForegroundColor White
}
finally {
    # 清理临时目录
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
    }
}
