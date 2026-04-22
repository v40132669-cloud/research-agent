#!/bin/bash
# 自动化研报 Agent 启动脚本 (Linux/Mac)

echo "=========================================="
echo "      自动化研报 Agent 启动脚本"
echo "=========================================="
echo ""

echo "[1/3] 检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.8+"
    read -p "按回车键退出"
    exit 1
fi

python3 --version
echo ""

echo "[2/3] 检查依赖..."
if ! python3 -c "import fastapi, uvicorn, jinja2" 2>/dev/null; then
    echo "检测到缺少依赖，正在安装..."
    if ! pip3 install -r requirements.txt; then
        echo "[错误] 依赖安装失败"
        read -p "按回车键退出"
        exit 1
    fi
    echo "依赖安装完成"
else
    echo "依赖检查通过"
fi
echo ""

echo "[3/3] 检查环境变量配置..."
if [ ! -f .env ]; then
    echo "[警告] 未找到 .env 文件"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "已创建 .env 文件，请补充 API Key"
    else
        echo "[警告] 也未找到 .env.example 模板文件"
    fi
else
    echo "环境变量配置已存在"
fi
echo ""

echo "=========================================="
echo "  启动 Web 服务..."
echo "  访问地址: http://localhost:8080"
echo "  按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

python3 web_app.py

read -p "按回车键退出"
