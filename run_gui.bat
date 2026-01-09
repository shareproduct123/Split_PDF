@echo off
REM Batch file to run PDF Splitter GUI
REM Double-click this file to start the application

echo ========================================
echo PDF Labor Agreement Splitter
echo ========================================
echo.
echo Starting GUI application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from python.org
    pause
    exit /b 1
)

REM Check if PyPDF2 is installed
python -c "import PyPDF2" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install PyPDF2
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Run the GUI
python gui_splitter.py

if errorlevel 1 (
    echo.
    echo Application closed with errors
    pause
)
