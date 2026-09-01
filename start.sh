#!/usr/bin/env bash
# Linux/macOS 一键启动

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "========================================"
echo "  成长学业追踪系统 · 一键启动"
echo "========================================"
echo ""

# 后端
echo "[1/3] 准备后端环境..."
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
    echo "  >> 创建 Python 虚拟环境..."
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "  [√] 后端依赖已就绪"

echo ""
echo "[2/3] 启动后端服务..."
python main.py &
BACKEND_PID=$!
sleep 2

# 前端
echo "[3/3] 准备前端环境..."
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
    echo "  >> 安装前端依赖..."
    npm install
fi
echo "  [√] 前端依赖已就绪"

echo ""
echo "========================================"
echo "  启动成功！"
echo "========================================"
echo ""
echo "  后端 API:  http://127.0.0.1:8000"
echo "  前端开发:  http://127.0.0.1:5173"
echo ""
echo "  按 Ctrl+C 关闭所有服务"
echo ""

npm run dev

# 退出时同时关闭后端
kill $BACKEND_PID 2>/dev/null || true
