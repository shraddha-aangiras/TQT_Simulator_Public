@echo off

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found.
    echo Please double-click the setup script first.
    echo.
    pause
    exit /b
)

call .venv\Scripts\activate

echo Starting application...
python interface.py

echo.
echo Application finished.
pause