@echo off
echo ==========================================
echo      自动化研报 Agent 启动脚本
echo ==========================================
echo.

if exist "%SystemRoot%\System32\chcp.com" (
    chcp 65001 >nul 2>&1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查 Python 版本...
python --version
echo.

echo [2/3] 检查依赖...
python -c "import fastapi, uvicorn, jinja2" >nul 2>&1
if errorlevel 1 (
    echo 检测到缺少依赖，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo 依赖安装完成
) else (
    echo 依赖检查通过
)
echo.

echo [3/3] 检查环境变量配置...
if not exist .env (
    echo [警告] 未找到 .env 文件，正在从模板创建...
    if exist .env.example (
        copy .env.example .env
        echo 已创建 .env 文件，请补充 API Key
    ) else (
        echo [警告] 也未找到 .env.example 模板文件
    )
) else (
    echo 环境变量配置已存在
)
echo.

echo ==========================================
echo  启动 Web 服务...
echo  访问地址: http://localhost:8080
echo  按 Ctrl+C 停止服务
echo ==========================================
echo.

python web_app.py

pause
