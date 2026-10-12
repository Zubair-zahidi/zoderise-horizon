@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ZPY="
if exist .venv\Scripts\python.exe set "ZPY=.venv\Scripts\python.exe"
if not defined ZPY if exist venv\Scripts\python.exe set "ZPY=venv\Scripts\python.exe"
if not defined ZPY (
  echo [ERROR] Run setup_windows.bat first.
  pause
  exit /b 1
)
echo Starting Zoderise Hub for this laptop and trusted devices...
"%ZPY%" launch.py --lan --with-ollama
if errorlevel 1 pause
endlocal
