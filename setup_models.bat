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
"%ZPY%" launch.py --with-ollama --check-models
if errorlevel 1 pause
endlocal
