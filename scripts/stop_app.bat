@echo off
setlocal
cd /d "%~dp0.."

where docker >nul 2>nul
if not errorlevel 1 (
  docker compose version >nul 2>&1
  if not errorlevel 1 (
    echo Stopping LogiSense Docker services...
    docker compose down --remove-orphans --volumes
    exit /b %ERRORLEVEL%
  )
)

echo Stopping local LogiSense services...
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 run.py stop
  if not errorlevel 1 exit /b 0
)

python run.py stop
