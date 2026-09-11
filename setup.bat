@echo off
cd /d "%~dp0"
py -3.13 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open start.bat.
pause
exit /b 0
:failed
echo Setup failed. Python 3.13 with tkinter is required.
pause
exit /b 1
