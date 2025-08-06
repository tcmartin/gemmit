#!/usr/bin/env pwsh
# PowerShell equivalent of build_backend.sh
param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"

# Get the root directory
$ROOT = Split-Path -Parent $PSScriptRoot
$PY = $PythonCommand

Write-Host "Building backend for Windows..." -ForegroundColor Green
Write-Host "Root directory: $ROOT" -ForegroundColor Yellow

# ── 1. Create virtual environment and install deps ─────────────
$VENV_DIR = Join-Path $ROOT "server\.venv"
if (!(Test-Path $VENV_DIR)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $PY -m venv $VENV_DIR
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment"
    }
}

# Activate virtual environment
$ActivateScript = Join-Path $VENV_DIR "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & $ActivateScript
} else {
    throw "Could not find activation script at $ActivateScript"
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow

# Use the virtual environment's Python to upgrade pip
$VenvPython = Join-Path $VENV_DIR "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Failed to upgrade pip, but continuing..." -ForegroundColor Yellow
}

$RequirementsPath = Join-Path $ROOT "server\requirements.txt"
& $VenvPython -m pip install -r $RequirementsPath pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install requirements"
}

# ── 2. Build one-file binary with static web assets ─────────────
Push-Location (Join-Path $ROOT "server")
try {
    Write-Host "Building backend binary..." -ForegroundColor Yellow
    
    $AppPath = Join-Path $ROOT "app"
    $GuidelinesPath = Join-Path $ROOT "ai_guidelines.md"
    $PocketflowPath = Join-Path $ROOT "pocketflowguide.md"
    
    & pyinstaller backend.py `
        --onefile `
        --name backend `
        --add-data "$AppPath;app" `
        --add-data "$GuidelinesPath;." `
        --add-data "$PocketflowPath;."
    
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed"
    }
} finally {
    Pop-Location
}

# ── 3. Move artefact next to Electron resources ─────────────────
Push-Location $ROOT
try {
    # Determine OS folder (Windows)
    $OS_FOLDER = "win"
    $BIN_DIR = Join-Path $ROOT "desktop\resources\bin\$OS_FOLDER"
    
    Write-Host "Creating binary directory: $BIN_DIR" -ForegroundColor Yellow
    if (!(Test-Path $BIN_DIR)) {
        New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null
    }
    
    # Move the backend.exe file
    $BackendExe = Join-Path $ROOT "server\dist\backend.exe"
    if (Test-Path $BackendExe) {
        Write-Host "Moving backend.exe to $BIN_DIR" -ForegroundColor Yellow
        Move-Item $BackendExe $BIN_DIR -Force
        Write-Host "✅ Backend binary placed in $BIN_DIR" -ForegroundColor Green
    } else {
        throw "Backend executable not found at $BackendExe"
    }
} finally {
    Pop-Location
}

Write-Host "🎉 Build completed successfully!" -ForegroundColor Green
