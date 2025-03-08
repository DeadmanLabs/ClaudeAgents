@echo off
setlocal enabledelayedexpansion

echo ClaudeAgents Run Script for Windows
echo ===================================

REM Default settings
set LANGUAGE=python
set VERBOSE=false
set PERSIST_MEMORY=false
set PROMPT_FILE=
set PROMPT=

REM Display help if requested
if "%~1"=="--help" goto :help
if "%~1"=="-h" goto :help

REM Process all command line arguments
:process_args
if "%~1"=="" goto :done_args

if "%~1"=="-l" (
    set LANGUAGE=%~2
    shift /1
    shift /1
    goto :process_args
)

if "%~1"=="--language" (
    set LANGUAGE=%~2
    shift /1
    shift /1
    goto :process_args
)

if "%~1"=="-v" (
    set VERBOSE=true
    shift /1
    goto :process_args
)

if "%~1"=="--verbose" (
    set VERBOSE=true
    shift /1
    goto :process_args
)

if "%~1"=="-p" (
    set PERSIST_MEMORY=true
    shift /1
    goto :process_args
)

if "%~1"=="--persist-memory" (
    set PERSIST_MEMORY=true
    shift /1
    goto :process_args
)

if "%~1"=="-f" (
    set PROMPT_FILE=%~2
    shift /1
    shift /1
    goto :process_args
)

if "%~1"=="--file" (
    set PROMPT_FILE=%~2
    shift /1
    shift /1
    goto :process_args
)

REM If not a recognized option, treat as prompt
set PROMPT=%~1
shift /1
goto :process_args

:help
echo Usage: run.bat [options] "prompt"
echo.
echo Options:
echo   -l, --language LANG     Language implementation to use (python, javascript)
echo   -v, --verbose           Enable verbose logging
echo   -p, --persist-memory    Persist agent memory between runs
echo   -f, --file FILE         Read prompt from file
echo.
echo Example:
echo   run.bat "Design a simple todo app"
echo   run.bat -l javascript -v -p -f example_prompt.txt
goto :EOF

:done_args
REM Show parsed arguments
echo Language: %LANGUAGE%
echo Verbose: %VERBOSE%
echo Persist Memory: %PERSIST_MEMORY%
echo Prompt File: %PROMPT_FILE%
echo Prompt: %PROMPT%
echo.

REM Validate settings
if "%LANGUAGE%" NEQ "python" (
    if "%LANGUAGE%" NEQ "javascript" (
        echo ERROR: Invalid language "%LANGUAGE%". Valid options are "python" or "javascript".
        exit /b 1
    )
)

if "%PROMPT_FILE%"=="" (
    if "%PROMPT%"=="" (
        echo ERROR: No prompt provided. Please provide a prompt or use -f to specify a prompt file.
        goto :help
    )
)

REM Handle Python implementation
if "%LANGUAGE%"=="python" (
    echo Running Python implementation...
    
    REM Validate Python installation
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH.
        exit /b 1
    )
    
    REM Set up virtual environment
    if not exist python\venv (
        echo Creating Python virtual environment...
        cd python
        python -m venv venv
        cd ..
    )
    
    REM Activate and install dependencies
    echo Installing dependencies...
    call python\venv\Scripts\activate.bat
    cd python
    python -m pip install --upgrade pip
    pip install -e . --upgrade
    pip install -r requirements.txt --upgrade
    cd ..
    
    REM Build command
    set CMD=python python\src\main.py
    
    if "%VERBOSE%"=="true" (
        set CMD=!CMD! --log-level DEBUG --log-to-file
    )
    
    if "%PERSIST_MEMORY%"=="true" (
        set CMD=!CMD! --persist-memory
    )
    
    if "%PROMPT_FILE%" NEQ "" (
        set CMD=!CMD! --prompt-file "%PROMPT_FILE%"
    ) else (
        set CMD=!CMD! "%PROMPT%"
    )
    
    REM Execute
    echo Executing: !CMD!
    !CMD!
    
    REM Clean up
    call deactivate
)

REM Handle JavaScript implementation
if "%LANGUAGE%"=="javascript" (
    echo Running JavaScript implementation...
    
    REM Validate Node.js installation
    node --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Node.js is not installed or not in PATH.
        exit /b 1
    )
    
    REM Install and build
    cd javascript
    echo Installing dependencies...
    call npm install
    
    echo Building project...
    call npm run build
    
    REM Build command
    set CMD=node dist\index.js
    
    if "%VERBOSE%"=="true" (
        set CMD=!CMD! --log-level debug --log-to-file
    )
    
    if "%PERSIST_MEMORY%"=="true" (
        set CMD=!CMD! --persist-memory
    )
    
    if "%PROMPT_FILE%" NEQ "" (
        set CMD=!CMD! --prompt-file "%PROMPT_FILE%"
    ) else (
        set CMD=!CMD! "%PROMPT%"
    )
    
    REM Execute
    echo Executing: !CMD!
    !CMD!
    
    cd ..
)

echo ClaudeAgents run completed.
endlocal