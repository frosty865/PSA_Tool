@echo off
REM Production Pattern Extractor - Windows Batch Wrapper
REM Ensures the script runs with the correct Python interpreter

REM Try to find Python in common locations
set PYTHON_PATH=

REM Check for Python in C:\Tools\python (project-specific location)
if exist "C:\Tools\python\python.exe" (
    set PYTHON_PATH=C:\Tools\python\python.exe
    goto :found
)

REM Check for Python in Program Files
if exist "C:\Program Files\Python311\python.exe" (
    set PYTHON_PATH=C:\Program Files\Python311\python.exe
    goto :found
)

REM Check for Python in Program Files (x86)
if exist "C:\Program Files (x86)\Python311\python.exe" (
    set PYTHON_PATH=C:\Program Files (x86)\Python311\python.exe
    goto :found
)

REM Check for py launcher
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_PATH=py -3
    goto :found
)

REM Check for python in PATH
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_PATH=python
    goto :found
)

REM If no Python found, show error
echo ERROR: Python not found. Please install Python 3.11 or later.
pause
exit /b 1

:found
echo Using Python: %PYTHON_PATH%
echo.
%PYTHON_PATH% "%~dp0extract_production_patterns.py" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo Script failed with error code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

