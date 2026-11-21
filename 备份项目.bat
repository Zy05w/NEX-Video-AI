@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "tools\backup.py"
) else (
  python "tools\backup.py"
)
pause
