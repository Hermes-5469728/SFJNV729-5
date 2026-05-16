@echo off
chcp 65001 >nul
echo AC 驾驶舱启动中...
cd /d "%~dp0"
start "" python ac_server.py
timeout /t 3 /nobreak >nul
start "" http://localhost:8001/site/index.html
echo 驾驶舱已启动
echo API: http://localhost:8001
echo 页面: http://localhost:8001/site/index.html
