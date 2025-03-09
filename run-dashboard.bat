@echo off
setlocal

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Docker is not installed. Please install Docker and try again.
    exit /b 1
)

REM Check if Docker Compose is installed
where docker-compose >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Docker Compose is not installed. Please install Docker Compose and try again.
    exit /b 1
)

REM Start the dashboard
echo Starting Claude Agents Dashboard...
docker-compose up --build

echo Claude Agents Dashboard is now running at http://localhost:5173

endlocal