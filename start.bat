@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   成长学业追踪系统 · 一键启动
echo ========================================
echo.

set "ROOT=%~dp0"

REM 后端
echo [1/3] 准备后端环境...
cd /d "%ROOT%backend"
if not exist ".venv" (
    echo   ^>^> 创建 Python 虚拟环境...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo   [√] 后端依赖已就绪

echo.
echo [2/3] 启动后端服务（新窗口）...
start "ChildStudy Backend" cmd /k "cd /d %ROOT%backend && .venv\Scripts\activate.bat && python main.py"

REM 等后端起来后显示本机 IP（方便手机/平板访问）
ping -n 3 127.0.0.1 >nul
for /f "tokens=2 delims=[]" %%a in ('python -c "import socket;s=socket.socket();s.connect(('8.8.8.8',80));print(s.getsockname()[0]);s.close()" 2^>nul') do set LAN_IP=%%a
if not defined LAN_IP for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R "IPv4.*[0-9]"') do (
  set "line=%%a"
  for /f "tokens=1" %%b in ("!line!") do set LAN_IP=%%b
)

REM 前端
echo [3/3] 准备前端环境...
cd /d "%ROOT%frontend"
if not exist "node_modules" (
    echo   ^>^> 安装前端依赖（首次需要几分钟）...
    call npm install
)
echo   [√] 前端依赖已就绪

echo.
echo ========================================
echo   启动成功！
echo ========================================
echo.
if defined LAN_IP (
  echo   本地地址:  http://127.0.0.1:5173
  echo   局域网访问: http://%LAN_IP%:5173
) else (
  echo   前端开发:  http://127.0.0.1:5173
)
echo   后端 API:  http://127.0.0.1:8000
echo.
if defined LAN_IP (
  echo   局域网内其他设备（手机/平板）打开上面 ^>LAN 访问^< 的地址即可
) else (
  echo   （未能自动检测局域网 IP，可在路由器里看本机 IP）
)
echo.
echo   首次使用会弹出 setup 向导：创建第一个家长账号
echo   关闭后端窗口即可停止服务
echo.

call npm run dev

pause
