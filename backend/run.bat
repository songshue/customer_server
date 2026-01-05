@echo off
echo 启动客服系统服务器...
cd /d "%~dp0"
python start_server.py
pause