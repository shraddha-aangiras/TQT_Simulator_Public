@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo Setting up Python Virtual Environment...

set "PY_COMMAND="

:: Try standard 'python' command
python --version >nul 2>&1
if %errorlevel% EQU 0 (
    set "PY_COMMAND=python"
    goto :FoundPython
)

:: Try Windows 'py' launcher
py --version >nul 2>&1
if %errorlevel% EQU 0 (
    set "PY_COMMAND=py"
    goto :FoundPython
)

:: Try finding Anaconda (Common paths)
echo Standard Python not found. Searching for Anaconda...
set "ANA_PATHS[1]=%USERPROFILE%\anaconda3"
set "ANA_PATHS[2]=%PROGRAMDATA%\Anaconda3"
set "ANA_PATHS[3]=%USERPROFILE%\miniconda3"
set "ANA_PATHS[4]=%LOCALAPPDATA%\Continuum\anaconda3"

for /F "tokens=2 delims==" %%A in ('set ANA_PATHS[') do (
    if exist "%%A\Scripts\activate.bat" (
        echo Found Anaconda at %%A
        call "%%A\Scripts\activate.bat" base
        set "PY_COMMAND=python"
        goto :FoundPython
    )
)

:: If we get here, absolutely nothing was found
echo.
echo [ERROR] Could not find Python or Anaconda automatically.
echo Please install Python from python.org OR open this script using "Anaconda Prompt".
echo.
pause
exit /b

:FoundPython
echo Using Python: %PY_COMMAND%

:: Remove old venv if it exists to ensure clean install
if exist ".venv" (
    echo Removing old .venv...
    rmdir /s /q .venv
)

"%PY_COMMAND%" -m venv .venv

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment was not created successfully.
    echo This often happens if "python" points to the Windows Store shortcut.
    echo.
    pause
    exit /b
)

call .venv\Scripts\activate

echo Installing requirements...
pip install -r requirements.txt

echo.
echo Setup Complete!
pause