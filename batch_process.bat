@echo off
REM Quick batch processing script
REM Drag and drop a folder onto this file to process all PDFs in it

echo ========================================
echo PDF Labor Agreement Splitter - Batch Mode
echo ========================================
echo.

if "%~1"=="" (
    echo ERROR: No folder specified
    echo.
    echo Usage: Drag and drop a folder onto this batch file
    echo        OR run: batch_process.bat "C:\path\to\folder"
    echo.
    pause
    exit /b 1
)

if not exist "%~1" (
    echo ERROR: Folder does not exist: %~1
    pause
    exit /b 1
)

echo Processing all PDFs in: %~1
echo.
echo Press Ctrl+C to cancel, or
pause

python split_agreement.py -b "%~1"

echo.
echo ========================================
echo Processing complete!
echo ========================================
echo.
echo Check the output folders for results.
echo Each PDF will have a [filename]_split folder.
echo.
pause
