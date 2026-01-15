@echo off
REM Setup script for Parallax Index virtual environment
REM Windows version

echo ==========================================
echo Parallax Index - Virtual Environment Setup
echo ==========================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    echo Please install Python 3.12 or higher
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
    set /p RECREATE="Do you want to recreate it? (y/N): "
    if /i "%RECREATE%"=="y" (
        echo Removing existing venv...
        rmdir /s /q venv
        python -m venv venv
        echo Virtual environment recreated
    ) else (
        echo Using existing virtual environment
    )
) else (
    python -m venv venv
    echo Virtual environment created
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo pip upgraded

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo Dependencies installed

REM Verify installation
echo.
echo Verifying installation...
python setup_check.py

echo.
echo ==========================================
echo Setup complete!
echo ==========================================
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate.bat
echo.
echo To start the application:
echo   python main.py
echo.
echo Or use VS Code tasks:
echo   Ctrl+Shift+P -^> Tasks: Run Task -^> Run: Start Application
echo.
pause
