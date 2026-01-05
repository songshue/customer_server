@echo off
chcp 65001 >nul
echo 启动客服系统Demo前端服务...
echo.

cd /d "%~dp0"
cd ..\..\frontend

echo 正在安装依赖包...
echo 这可能需要几分钟时间，请耐心等待...
echo.

npm install

if %errorlevel% neq 0 (
    echo npm install 失败，请检查npm配置或网络连接
    pause
    exit /b 1
)

echo.
echo 依赖包安装完成，正在启动开发服务器...
echo 前端地址: http://localhost:3000
echo.
echo 按Ctrl+C停止服务
echo.

npm run dev