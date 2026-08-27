@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo Starting BizVision AI...
echo Project: %cd%

"%PYTHON_EXE%" -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Streamlit is not installed for this Python. Installing project requirements...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Installation failed. Please install Python and run:
        echo python -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

"%PYTHON_EXE%" -m streamlit run app.py
pause
