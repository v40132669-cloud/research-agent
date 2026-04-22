#!/usr/bin/env pwsh
# 自动化研报 Agent 启动脚本 (PowerShell)

$Host.UI.RawUI.WindowTitle = "自动化研报 Agent"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "      自动化研报 Agent 启动脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] 检查 Python 版本..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python 版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未检测到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

Write-Host "[2/3] 检查依赖..." -ForegroundColor Yellow
try {
    $null = python -c "import fastapi, uvicorn, jinja2" 2>&1
    Write-Host "依赖检查通过" -ForegroundColor Green
} catch {
    Write-Host "检测到缺少依赖，正在安装..." -ForegroundColor Yellow
    try {
        pip install -r requirements.txt
        Write-Host "依赖安装完成" -ForegroundColor Green
    } catch {
        Write-Host "[错误] 依赖安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}
Write-Host ""

Write-Host "[3/3] 检查环境变量配置..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Write-Host "[警告] 未找到 .env 文件" -ForegroundColor Yellow
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "已创建 .env 文件，请补充 API Key" -ForegroundColor Green
    } else {
        Write-Host "[警告] 也未找到 .env.example 模板文件" -ForegroundColor Yellow
    }
} else {
    Write-Host "环境变量配置已存在" -ForegroundColor Green
}
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  启动 Web 服务..." -ForegroundColor Green
Write-Host "  访问地址: " -NoNewline
Write-Host "http://localhost:8080" -ForegroundColor Yellow
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

python web_app.py

Read-Host "按回车键退出"
