@echo off
REM HV Screener Setup Script for Windows
REM This script sets up the Historical Volatility Screener application

echo ========================================================
echo   Historical Volatility Screener - Setup Script
echo ========================================================
echo.

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

python --version
echo Python found!
echo.

REM Check pip
echo Checking pip installation...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed
    echo Installing pip...
    python -m ensurepip --upgrade
)
echo pip found!
echo.

REM Ask about virtual environment
set /p VENV="Create a virtual environment? (recommended) [Y/n]: "
if /i "%VENV%"=="y" goto CreateVenv
if /i "%VENV%"=="" goto CreateVenv
goto SkipVenv

:CreateVenv
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo Virtual environment created and activated!
echo.

:SkipVenv
REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo Dependencies installed successfully!
echo.

REM Check for asset_list.csv
echo Checking for asset_list.csv...
if exist "asset_list.csv" (
    echo asset_list.csv found!
    for /f %%i in ('find /c /v "" ^< asset_list.csv') do set LINES=%%i
    set /a ASSETS=%LINES%-1
    echo   ^> %ASSETS% assets loaded
) else (
    echo [WARNING] asset_list.csv not found
    echo   ^> You can upload it via the web interface when running the app
)
echo.

REM Create .streamlit directory
if not exist ".streamlit" (
    echo Creating .streamlit configuration directory...
    mkdir .streamlit
)

echo ========================================================
echo   Setup Complete! 🎉
echo ========================================================
echo.
echo To run the application:
echo.
if /i "%VENV%"=="y" (
    echo   1. Activate virtual environment: venv\Scripts\activate
)
if /i "%VENV%"=="" (
    echo   1. Activate virtual environment: venv\Scripts\activate
)
echo   2. Run the app: streamlit run hv_screener_enhanced.py
echo.
echo The app will open in your browser at http://localhost:8501
echo.
echo For deployment instructions, see DEPLOYMENT_GUIDE.md
echo.
pause
