@echo off
title Agent V1 Pro 安装向导
echo 正在检查 Python 环境...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 未找到 Python，正在尝试自动安装（需要网络）...
    powershell -Command "Start-Process winget -ArgumentList 'install', 'Python.Python.3.11', '--silent' -Wait"
)

echo 正在启动图形界面...
python install_gui.py
if %errorlevel% neq 0 (
    echo 启动失败，请确保已经安装了 Python 和 Tkinter。
    pause
)