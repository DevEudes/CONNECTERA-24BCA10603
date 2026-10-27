@echo off
REM Connectera - start the app (Windows). Double-click this file or run "run.bat" in a terminal.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [X] The project is not installed yet: run setup.bat first.
    pause
    exit /b 1
)
echo Connectera is starting... it will open in your browser: http://127.0.0.1:8000
echo (Press CTRL+C in this window to stop the server.)
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" manage.py runserver
pause
