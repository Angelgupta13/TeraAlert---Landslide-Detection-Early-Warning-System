@echo off
echo ================================================
echo   TeraAlert - Landslide Detection System
echo   Starting Backend Server...
echo ================================================
echo.

cd /d "%~dp0"
cd backend

echo [1] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

echo [2] Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
)

echo [3] Starting server...
echo.
echo ================================================
echo   Server will start at: http://localhost:8000
echo   Dashboard: http://localhost:8000/dashboard
echo   API Docs:  http://localhost:8000/docs
echo ================================================
echo.
echo Press Ctrl+C to stop the server.
echo.

python main.py

pause
