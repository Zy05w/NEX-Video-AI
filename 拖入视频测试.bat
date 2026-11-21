@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" "tools\drag_test.py" %*
pause
