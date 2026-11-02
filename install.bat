@echo off
setlocal enabledelayedexpansion
title Agent V1 Pro Installer

echo ======================================================
echo        Agent V1 Pro Installer (Windows)
echo ======================================================

set "INSTALL_DIR=%USERPROFILE%\.agent_v1pro"

:: 1. 判断安装模式
if exist "main.py" (
    echo [INFO] Detected local installation mode...
    set "INSTALL_DIR=%cd%"
) else (
    echo [INFO] Detected online bootstrap mode...
    where git >nul 2>nul
    if !errorlevel! neq 0 (
        echo [ERROR] Git is not installed. Please install Git from https://git-scm.com/ first.
        pause
        exit /b 1
    )
    
    if exist "%INSTALL_DIR%\.git" (
        echo [INFO] Updating existing repository...
        cd /d "%INSTALL_DIR%"
        git pull
    ) else (
        echo [INFO] Cloning repository to %INSTALL_DIR% ...
        git clone https://github.com/3344345/agent_v1pro.git "%INSTALL_DIR%"
        cd /d "%INSTALL_DIR%"
    )
)

cd /d "%INSTALL_DIR%"

:: 2. 检查 Python
python --version >nul 2>nul
if !errorlevel! neq 0 (
    echo [WARNING] Python not found in PATH.
    echo [INFO] Trying to install Python 3.11 via winget...
    winget install Python.Python.3.11 --silent
    echo [INFO] Please restart this script after Python installation completes.
    pause
    exit /b 1
)

:: 3. 拉起 GUI
echo [INFO] Starting graphical setup wizard...
python install_gui.py

if !errorlevel! neq 0 (
    echo [ERROR] Setup failed or cancelled.
    pause
)