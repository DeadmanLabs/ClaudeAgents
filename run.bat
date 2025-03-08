@echo off
setlocal enabledelayedexpansion

:: Run script for ClaudeAgents (Windows)

echo ClaudeAgents Run Script for Windows
echo ===================================

:: Check for help flag
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
goto :continue_execution

:show_help
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
    echo   run.bat -l javascript -v -p -f prompt.txt
    exit /b 0

:continue_execution

:: Default configuration
set LANGUAGE=python
set VERBOSE=false
set PERSIST_MEMORY=false
set PROMPT_FILE=
set PROMPT=

:: Parse command line arguments
:parse_args
if "%~1"=="" goto end_parse_args

if /i "%~1"=="-l" (
    set LANGUAGE=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--language" (
    set LANGUAGE=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-v" (
    set VERBOSE=true
    shift
    goto parse_args
)
if /i "%~1"=="--verbose" (
    set VERBOSE=true
    shift
    goto parse_args
)
if /i "%~1"=="-p" (
    set PERSIST_MEMORY=true
    shift
    goto parse_args
)
if /i "%~1"=="--persist-memory" (
    set PERSIST_MEMORY=true
    shift
    goto parse_args
)
if /i "%~1"=="-f" (
    set PROMPT_FILE=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--file" (
    set PROMPT_FILE=%~2
    shift
    shift
    goto parse_args
)

:: If we get here, assume it's the prompt
set PROMPT=%~1
shift
goto parse_args

:end_parse_args

echo Language: %LANGUAGE%
echo Verbose: %VERBOSE%
echo Persist Memory: %PERSIST_MEMORY%
echo Prompt File: %PROMPT_FILE%
echo Prompt: %PROMPT%

:: If the first parameter after options is "f", it's likely meant to be "-f" that got separated
if not "%PROMPT_FILE%"=="" if "%PROMPT%"=="f" (
    echo Note: Detected "f" as prompt and file parameter already set. This is likely an error.
    echo For file input, use: run.bat -f your_file.txt
) else if "%PROMPT%"=="f" (
    echo Note: Detected "f" as the prompt. Did you mean to use "-f" for file input?
    echo For file input, use: run.bat -f your_file.txt
)

:: Validate language choice
if /i "%LANGUAGE%" NEQ "python" if /i "%LANGUAGE%" NEQ "javascript" (
    echo ERROR: Invalid language selection. Choose 'python' or 'javascript'.
    exit /b 1
)

:: Check environmental variables
if "%ANTHROPIC_API_KEY%"=="" if "%OPENAI_API_KEY%"=="" (
    echo WARNING: Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY environment variables are set.
    echo The agents will not be able to make API calls to AI services.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i "!CONTINUE!" NEQ "y" exit /b 1
)

:: Check for Python environment and dependencies for Python implementation
if /i "%LANGUAGE%"=="python" (
    echo Checking Python environment...
    
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH.
        exit /b 1
    )
    
    :: Create virtual environment if it doesn't exist
    if not exist python\venv (
        echo Creating Python virtual environment...
        cd python
        python -m venv venv
        cd ..
    )
    
    :: Activate virtual environment and install dependencies
    echo Activating virtual environment and installing dependencies...
    call python\venv\Scripts\activate.bat
    cd python
    pip install -e . --upgrade
    pip install -r requirements.txt --upgrade
    cd ..
    
    :: Prepare command
    set CMD=python python\src\main.py
    
    if "%VERBOSE%"=="true" (
        set CMD=!CMD! --log-level DEBUG --log-to-file
    )
    
    if "%PERSIST_MEMORY%"=="true" (
        set CMD=!CMD! --persist-memory
    )
    
    if not "%PROMPT_FILE%"=="" (
        set CMD=!CMD! --prompt-file "%PROMPT_FILE%"
    ) else if not "%PROMPT%"=="" (
        set CMD=!CMD! "%PROMPT%"
    ) else (
        echo ERROR: No prompt provided. Use the -f option for a file or provide a prompt as an argument.
        call deactivate
        exit /b 1
    )
    
    :: Run Python implementation
    echo Running Python implementation...
    echo Command: !CMD!
    !CMD!
    
    :: Deactivate virtual environment
    call deactivate
)

:: Check for Node.js and dependencies for JavaScript implementation
if /i "%LANGUAGE%"=="javascript" (
    echo Checking Node.js environment...
    
    node --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Node.js is not installed or not in PATH.
        exit /b 1
    )
    
    npm --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: npm is not installed or not in PATH.
        exit /b 1
    )
    
    :: Install dependencies
    echo Installing dependencies...
    cd javascript
    call npm install
    
    :: Build the project
    echo Building project...
    call npm run build
    
    :: Prepare command
    set CMD=node dist\index.js
    
    if "%VERBOSE%"=="true" (
        set CMD=!CMD! --log-level debug --log-to-file
    )
    
    if "%PERSIST_MEMORY%"=="true" (
        set CMD=!CMD! --persist-memory
    )
    
    if not "%PROMPT_FILE%"=="" (
        set CMD=!CMD! --prompt-file "%PROMPT_FILE%"
    ) else if not "%PROMPT%"=="" (
        set CMD=!CMD! "%PROMPT%"
    ) else (
        echo ERROR: No prompt provided. Use the -f option for a file or provide a prompt as an argument.
        cd ..
        exit /b 1
    )
    
    :: Run JavaScript implementation
    echo Running JavaScript implementation...
    echo Command: !CMD!
    !CMD!
    
    cd ..
)

echo ClaudeAgents run completed.
endlocal