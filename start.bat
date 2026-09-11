@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
start "MPU Monitor" ".venv\Scripts\pythonw.exe" monitor.py
