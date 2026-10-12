@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ZPY="
if exist .venv\Scripts\python.exe set "ZPY=.venv\Scripts\python.exe"
if not defined ZPY if exist venv\Scripts\python.exe set "ZPY=venv\Scripts\python.exe"
if not defined ZPY (
  py -3.12 -m venv .venv
  if errorlevel 1 py -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo [ERROR] Install Python 3.12 or newer and try again.
    pause
    exit /b 1
  )
  set "ZPY=.venv\Scripts\python.exe"
)
"%ZPY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependency installation failed.
  pause
  exit /b 1
)
if not exist .env copy .env.example .env >nul
echo Setup complete. Run start_ollama_and_zoderise.bat.
pause
endlocal
