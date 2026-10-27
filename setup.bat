@echo off
REM Connectera - installation (Windows). Double-click this file or run "setup.bat" in a terminal.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 setup_project.py
    goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
    python setup_project.py
    goto end
)
echo.
echo [X] Python is not installed.
echo     Download it from https://www.python.org/downloads/
echo     IMPORTANT: tick "Add python.exe to PATH" during the installation, then run setup.bat again.

:end
echo.
pause
