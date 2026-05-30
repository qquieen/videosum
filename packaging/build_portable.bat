@echo off
REM VideoSum 一键运行版打包脚本
REM 需要先安装: pip install pyinstaller

echo ========================================
echo VideoSum 一键运行版打包脚本
echo ========================================

REM 创建输出目录
if not exist "release" mkdir release
if not exist "release\portable" mkdir "release\portable"

echo.
echo [1/4] 安装PyInstaller...
pip install pyinstaller

echo.
echo [2/4] 打包主程序...
pyinstaller ^
    --name VideoSum ^
    --onedir ^
    --console ^
    --noconfirm ^
    --clean ^
    --add-data "videosum\i18n;videosum\i18n" ^
    --hidden-import gradio ^
    --hidden-import gradio.themes ^
    --hidden-import faster_whisper ^
    --hidden-import openai ^
    --hidden-import yaml ^
    --hidden-import requests ^
    main.py

echo.
echo [3/4] 复制依赖文件...

REM 复制requirements.txt
copy requirements.txt "release\portable\"

REM 复制README
copy README.md "release\portable\"

REM 创建说明文件
echo VideoSum 一键运行版 > "release\portable\使用说明.txt"
echo. >> "release\portable\使用说明.txt"
echo 使用方法: >> "release\portable\使用说明.txt"
echo 1. 确保已安装Python 3.10+ >> "release\portable\使用说明.txt"
echo 2. 运行: pip install -r requirements.txt >> "release\portable\使用说明.txt"
echo 3. 运行: python main.py >> "release\portable\使用说明.txt"
echo. >> "release\portable\使用说明.txt"
echo 需要单独安装: >> "release\portable\使用说明.txt"
echo - FFmpeg: https://ffmpeg.org/download.html >> "release\portable\使用说明.txt"
echo - yt-dlp: pip install yt-dlp >> "release\portable\使用说明.txt"
echo - Ollama (可选): https://ollama.ai >> "release\portable\使用说明.txt"

echo.
echo [4/4] 打包完成！
echo 输出目录: release\portable\VideoSum\

pause
