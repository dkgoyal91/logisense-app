@echo off
setlocal EnableDelayedExpansion
set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

where docker >nul 2>nul
if not errorlevel 1 (
  docker compose version >nul 2>&1
  if not errorlevel 1 (
    echo Stopping LogiSense Docker services...
    docker compose down --remove-orphans --volumes
    if not errorlevel 1 exit /b 0
  )
)

where docker-compose >nul 2>nul
if not errorlevel 1 (
  docker-compose version >nul 2>&1
  if not errorlevel 1 (
    echo Stopping LogiSense Docker services...
    docker-compose down --remove-orphans --volumes
    if not errorlevel 1 exit /b 0
  )
)

where wsl.exe >nul 2>nul
if not errorlevel 1 (
  for /f "usebackq delims=" %%I in (`wsl.exe wslpath "%ROOT_DIR%" 2^>nul`) do set "WSL_ROOT_DIR=%%I"
  if not "!WSL_ROOT_DIR!"=="" (
    wsl.exe bash -lc "docker compose version >/dev/null 2>&1" 2>nul
    if not errorlevel 1 (
      echo Stopping LogiSense Docker services via WSL...
      wsl.exe bash -lc "cd '!WSL_ROOT_DIR!' && docker compose down --remove-orphans --volumes" 2>nul
      if not errorlevel 1 exit /b 0
    )
  )
)

echo Stopping local LogiSense services...
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 run.py stop
  if not errorlevel 1 exit /b 0
)

python run.py stop
