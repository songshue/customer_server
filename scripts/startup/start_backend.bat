@echo off
chcp 65001 >nul
echo 启动客服系统Demo后端服务...
echo.

cd /d "%~dp0"
cd ..\..\backend

echo 正在启动FastAPI服务...
echo 服务地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 按Ctrl+C停止服务
echo.

python main.py