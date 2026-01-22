@echo off

cd /d "%~dp0.."
echo Setting up Python Virtual Environment...

python -m venv .venv
call .venv\Scripts\activate

echo Installing requirements...
pip install -r requirements.txt

echo Setup Complete!
cmd /k