@echo off
setlocal enabledelayedexpansion

echo Building backend for Windows...

REM Get the root directory
set ROOT=%~dp0..
set PY=python

echo Root directory: %ROOT%

REM ── 1. Create virtual environment and install deps ─────────────
set VENV_DIR=%ROOT%\server\.venv
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    %PY% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create virtual environment
        exit /b 1
    )
)

REM Activate virtual environment
set ACTIVATE_SCRIPT=%VENV_DIR%\Scripts\activate.bat
if exist "%ACTIVATE_SCRIPT%" (
    echo Activating virtual environment...
    call "%ACTIVATE_SCRIPT%"
) else (
    echo Could not find activation script at %ACTIVATE_SCRIPT%
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip
    exit /b 1
)

pip install -r "%ROOT%\server\requirements.txt" pyinstaller
if errorlevel 1 (
    echo Failed to install requirements
    exit /b 1
)

REM ── 2. Build one-file binary with static web assets ─────────────
pushd "%ROOT%\server"
echo Building backend binary...

pyinstaller backend.py ^
    --onefile ^
    --name backend ^
    --add-data "%ROOT%\app;app" ^
    --add-data "%ROOT%\ai_guidelines.md;." ^
    --add-data "%ROOT%\pocketflowguide.md;."

if errorlevel 1 (
    echo PyInstaller failed
    popd
    exit /b 1
)
popd

REM ── 3. Move artefact next to Electron resources ─────────────────
set OS_FOLDER=win
set BIN_DIR=%ROOT%\desktop\resources\bin\%OS_FOLDER%

echo Creating binary directory: %BIN_DIR%
if not exist "%BIN_DIR%" (
    mkdir "%BIN_DIR%"
)

REM Move the backend.exe file
set BACKEND_EXE=%ROOT%\server\dist\backend.exe
if exist "%BACKEND_EXE%" (
    echo Moving backend.exe to %BIN_DIR%
    move "%BACKEND_EXE%" "%BIN_DIR%\"
    echo ✅ Backend binary placed in %BIN_DIR%
) else (
    echo Backend executable not found at %BACKEND_EXE%
    exit /b 1
)

echo 🎉 Build completed successfully!
