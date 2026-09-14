@echo off
setlocal
cd /d "%~dp0.."

where docker >nul 2>nul
if not errorlevel 1 (
  docker compose version >nul 2>&1
  if not errorlevel 1 (
    echo Starting LogiSense using Docker Compose...
    docker compose up --build -d
    exit /b %ERRORLEVEL%
  )
)

echo Docker Compose not available; starting the local Python app...
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 run.py local
  if not errorlevel 1 exit /b 0
)

python run.py local
