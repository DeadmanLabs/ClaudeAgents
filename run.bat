@echo off
setlocal enabledelayedexpansion

rem Run script for ClaudeAgents (Windows)

echo ClaudeAgents Run Script for Windows
echo ===================================

rem Check for help flag
if /i "%~1"=="--help" goto display_help
if /i "%~1"=="-h" goto display_help

rem Default configuration
set LANGUAGE=python
set VERBOSE=false
set PERSIST_MEMORY=false
set PROMPT_FILE=
set PROMPT=

rem Parse command line arguments
:parse_args
if "%~1"=="" goto run_program

if /i "%~1"=="-l" (
    if "%~2"=="" (
        echo ERROR: Language option requires a value.
        exit /b 1
    )
    set LANGUAGE=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--language" (
    if "%~2"=="" (
        echo ERROR: Language option requires a value.
        exit /b 1
    )
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
    if "%~2"=="" (
        echo ERROR: File option requires a filename.
        exit /b 1
    )
    set PROMPT_FILE=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--file" (
    if "%~2"=="" (
        echo ERROR: File option requires a filename.
        exit /b 1
    )
    set PROMPT_FILE=%~2
    shift
    shift
    goto parse_args
)

rem If we get here, assume it's the prompt
set PROMPT=%~1
shift
goto parse_args

rem Display help information
:display_help
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
exit /b 0

rem Run the program
:run_program
echo Language: %LANGUAGE%
echo Verbose: %VERBOSE%
echo Persist Memory: %PERSIST_MEMORY% 
echo Prompt File: %PROMPT_FILE%
echo Prompt: %PROMPT%

rem Check for common errors
if "%PROMPT%"=="f" (
    echo WARNING: "f" specified as prompt. Did you mean to use -f for file input?
    echo For file input, use: run.bat -f example_prompt.txt
    echo.
    set /p CONTINUE=Continue with "f" as the prompt? (y/n): 
    if /i "!CONTINUE!" NEQ "y" exit /b 1
)

rem Validate language choice
if /i "%LANGUAGE%" NEQ "python" if /i "%LANGUAGE%" NEQ "javascript" (
    echo ERROR: Invalid language selection '%LANGUAGE%'. Choose 'python' or 'javascript'.
    exit /b 1
)

rem Check if no prompt provided
if "%PROMPT_FILE%"=="" if "%PROMPT%"=="" (
    echo ERROR: No prompt provided. Use the -f option for a file or provide a prompt as an argument.
    goto display_help
)

rem Check environmental variables
if "%ANTHROPIC_API_KEY%"=="" if "%OPENAI_API_KEY%"=="" (
    echo WARNING: Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY environment variables are set.
    echo The agents will not be able to make API calls to AI services.
    set /p CONTINUE=Continue anyway? (y/n): 
    if /i "!CONTINUE!" NEQ "y" exit /b 1
)

rem Run the chosen implementation
if /i "%LANGUAGE%"=="python" (
    goto run_python
) else (
    goto run_javascript
)

rem Run the Python implementation
:run_python
echo Checking Python environment...

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    exit /b 1
)

rem Create virtual environment if it doesn't exist
if not exist python\venv (
    echo Creating Python virtual environment...
    cd python
    python -m venv venv
    cd ..
)

rem Activate virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call python\venv\Scripts\activate.bat
cd python
pip install -e . --upgrade
pip install -r requirements.txt --upgrade
cd ..

rem Prepare command
set CMD=python python\src\main.py

if "%VERBOSE%"=="true" (
    set CMD=!CMD! --log-level DEBUG --log-to-file
)

if "%PERSIST_MEMORY%"=="true" (
    set CMD=!CMD! --persist-memory
)

if not "%PROMPT_FILE%"=="" (
    set CMD=!CMD! --prompt-file "%PROMPT_FILE%"
) else (
    set CMD=!CMD! "%PROMPT%"
)

rem Run Python implementation
echo Running Python implementation...
echo Command: !CMD!
!CMD!

rem Deactivate virtual environment
call deactivate
goto end

rem Run the JavaScript implementation
:run_javascript
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

rem Install dependencies
echo Installing dependencies...
cd javascript
call npm install

rem Build the project
echo Building project...
call npm run build

rem Prepare command
set CMD=node dist\index.js

if "%VERBOSE%"=="true" (
    set CMD=!CMD! --log-level debug --log-to-file
)

if "%PERSIST_MEMORY%"=="true" (
    set CMD=!CMD! --persist-memory
)

if not "%PROMPT_FILE%"=="" (
    set CMD=!CMD! --prompt-file "%PROMPT_FILE%"
) else (
    set CMD=!CMD! "%PROMPT%"
)

rem Run JavaScript implementation
echo Running JavaScript implementation...
echo Command: !CMD!
!CMD!

cd ..
goto end

:end
echo ClaudeAgents run completed.
endlocal