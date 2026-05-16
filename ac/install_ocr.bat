@echo off
chcp 65001 > nul
title 医学课本OCR工具安装
echo === 安装 Tesseract OCR（含中文语言包）===
echo.

:: 方案1: 清华镜像（国内推荐）
echo 从清华镜像下载 Tesseract...
curl -L -o tesseract-installer.exe "https://mirrors.tuna.tsinghua.edu.cn/github-release/UB-Mannheim/tesseract/LatestRelease/tesseract-ocr-w64-setup-5.3.3.20231005.exe"

if not exist tesseract-installer.exe (
    echo 清华镜像失败，尝试其他源...
    curl -L -o tesseract-installer.exe "https://ghproxy.com/https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
)

if exist tesseract-installer.exe (
    start /wait tesseract-installer.exe /S
    echo Tesseract 安装完成
) else (
    echo 下载失败，请手动安装 Tesseract:
    echo 下载地址: https://mirrors.tuna.tsinghua.edu.cn/github-release/UB-Mannheim/tesseract/
    echo 选择 tesseract-ocr-w64-setup-5.3.3.20231005.exe
    pause
)

:: 安装中文语言包
set TESSDATA=C:\Program Files\Tesseract-OCR\tessdata
if exist "%TESSDATA%" (
    echo 下载中文语言包...
    curl -L -o "%TESSDATA%\chi_sim.traineddata" "https://ghproxy.com/https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata"
)

:: 安装 Python 依赖
echo.
echo === 安装 Python 依赖 ===
pip install pytesseract pillow -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo === 安装完成 ===
echo 用法:
echo   单文件: python ocr_med.py D:\path\photo.jpg
echo   批量:   python ocr_med.py D:\36854\临床医学\内科学
echo.
pause
