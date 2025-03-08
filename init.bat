@echo off
setlocal enabledelayedexpansion

:: Initialization script for ClaudeAgents (Windows)

echo ClaudeAgents Initialization Script for Windows
echo =============================================

:: Check Python environment
echo Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org and ensure it's in your PATH.
    exit /b 1
)

:: Check Node.js environment
echo Checking Node.js environment...
node --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Node.js is not installed or not in PATH.
    echo The JavaScript implementation will not be available.
    echo Please install Node.js 18+ from https://nodejs.org if you want to use the JavaScript implementation.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i "!CONTINUE!" NEQ "y" exit /b 1
) else (
    npm --version >nul 2>&1
    if errorlevel 1 (
        echo WARNING: npm is not installed or not in PATH.
        echo The JavaScript implementation will not be available.
        set /p CONTINUE="Continue anyway? (y/n): "
        if /i "!CONTINUE!" NEQ "y" exit /b 1
    )
)

:: Set up Python virtual environment
echo Setting up Python environment...
if not exist python\venv (
    echo Creating Python virtual environment...
    cd python
    python -m venv venv
    cd ..
)

:: Set up Python dependencies
echo Installing Python dependencies...
call python\venv\Scripts\activate.bat
cd python
python -m pip install --upgrade pip
pip install wheel setuptools --upgrade
pip install -e . --upgrade
pip install -r requirements.txt --upgrade
cd ..
call deactivate

:: Set up JavaScript dependencies (if Node.js is available)
node --version >nul 2>&1
if not errorlevel 1 (
    echo Setting up JavaScript environment...
    cd javascript
    npm install
    npm run build
    cd ..
)

:: Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit the .env file to add your API keys.
)

:: Create example prompt
if not exist example_prompt.txt (
    echo Creating example prompt...
    echo "Design a simple command-line calculator app with basic arithmetic operations." > example_prompt.txt
)

echo.
echo ClaudeAgents initialized successfully!
echo.
echo You can now run the system using:
echo   run.bat "Your prompt here"
echo or
echo   run.bat -f example_prompt.txt
echo.
echo For more options, run:
echo   run.bat --help

endlocal