@echo off
echo 启动客服系统 Docker 环境...
echo.

REM 检查Docker是否运行
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：Docker未运行，请先启动Docker Desktop
    pause
    exit /b 1
)

REM 询问用户选择启动模式
echo 请选择启动模式：
echo 1. 完整Docker环境 (推荐)
echo 2. 开发模式 (本地运行前后端 + Docker数据库)
echo 3. 仅启动数据库和Redis
echo.
set /p choice=请输入选择 (1-3): 

if "%choice%"=="1" (
    echo 启动完整Docker环境...
    docker-compose up --build -d
    echo.
    echo 等待服务启动...
    timeout /t 30 /nobreak >nul
    echo.
    echo 启动完成！访问地址：
    echo - 后端API: http://localhost:8000
    echo - API文档: http://localhost:8000/docs
    echo - 前端界面: http://localhost:80
    echo - Prometheus监控: http://localhost:9090
    echo.
    echo 查看日志：docker-compose logs -f
    echo 停止服务：docker-compose down
)

if "%choice%"=="2" (
    echo 启动开发模式...
    docker-compose up -d mysql redis
    echo.
    echo 等待数据库启动...
    timeout /t 15 /nobreak >nul
    echo.
    echo 请在新的终端窗口中运行：
    echo 后端：cd backend ^&^& python -m uvicorn app.main:app --reload
    echo 前端：cd frontend ^&^& npm run dev
    echo.
    echo 启动完成！访问地址：
    echo - 后端API: http://localhost:8000
    echo - 前端界面: http://localhost:5173
)

if "%choice%"=="3" (
    echo 仅启动数据库和Redis...
    docker-compose up -d mysql redis
    echo.
    echo 启动完成！
    echo - MySQL: localhost:3306 (root/011216)
    echo - Redis: localhost:6379
    echo.
    echo 查看状态：docker-compose ps
    echo 停止服务：docker-compose down
)

echo.
echo 按任意键退出...
pause >nul