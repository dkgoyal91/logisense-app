@echo off
setlocal EnableDelayedExpansion
set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

where docker >nul 2>nul
if not errorlevel 1 (
  docker compose version >nul 2>&1
  if not errorlevel 1 (
    echo Starting LogiSense using Docker Compose...
    docker compose up --build -d
    if not errorlevel 1 exit /b 0
  )
)

where docker-compose >nul 2>nul
if not errorlevel 1 (
  docker-compose version >nul 2>&1
  if not errorlevel 1 (
    echo Starting LogiSense using Docker Compose...
    docker-compose up --build -d
    if not errorlevel 1 exit /b 0
  )
)

where wsl.exe >nul 2>nul
if not errorlevel 1 (
  for /f "usebackq delims=" %%I in (`wsl.exe wslpath "%ROOT_DIR%" 2^>nul`) do set "WSL_ROOT_DIR=%%I"
  if not "!WSL_ROOT_DIR!"=="" (
    wsl.exe bash -lc "docker compose version >/dev/null 2>&1" 2>nul
    if not errorlevel 1 (
      echo Starting LogiSense using Docker Compose via WSL...
      wsl.exe bash -lc "cd '!WSL_ROOT_DIR!' && docker compose up --build -d" 2>nul
      if not errorlevel 1 exit /b 0
    )
  )
)

echo Docker Compose not available or failed; starting the local Python app...
where py >nul 2>nul
if not errorlevel 1 (
  py -3.13 run.py local
  if not errorlevel 1 exit /b 0
  py -3.12 run.py local
  if not errorlevel 1 exit /b 0
)

where python3.13 >nul 2>nul
if not errorlevel 1 (
  python3.13 run.py local
  if not errorlevel 1 exit /b 0
)

where python3.12 >nul 2>nul
if not errorlevel 1 (
  python3.12 run.py local
  if not errorlevel 1 exit /b 0
)

python run.py local
