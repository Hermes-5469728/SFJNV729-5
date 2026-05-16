@echo off
chcp 65001 >nul
title AC Server · Hermes Platform
echo [AC] 启动 AC Server ...
:restart
python "%~dp0ac_server.py"
echo [AC] 服务已退出，5 秒后重启 ...
timeout /t 5 /nobreak >nul
goto restart
