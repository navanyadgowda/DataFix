@echo off
echo =====================================================================
echo        DataFix - Autonomous Data Quality and Repair Engine
echo =====================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your PATH.
    echo Please install Python 3.10+ and add it to your system PATH.
    pause
    exit /b 1
)

:: Virtual environment setup
if not exist "venv" (
    echo [INFO] Creating Python virtual environment in .\venv ...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Updating pip and installing dependencies with extended timeout...
python -m pip install --upgrade pip
pip install --default-timeout=100 -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Encountered network issues with some packages. Installing core engine...
    pip install --default-timeout=100 streamlit pandas numpy openpyxl
)

echo.
echo =====================================================================
echo [INFO] Launching DataFix Dashboard on http://localhost:8501 ...
echo =====================================================================
echo.
streamlit run app.py

pause
