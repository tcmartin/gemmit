#!/usr/bin/env pwsh
# PowerShell equivalent of fetch_node_runtimes.sh
param(
    [string]$NodeVersion = "20.11.1"
)

$ErrorActionPreference = "Stop"

# Get the root directory  
$ROOT = Split-Path -Parent $PSScriptRoot
$DESKTOP_DIR = Join-Path $ROOT "desktop"
$RESOURCES_DIR = Join-Path $DESKTOP_DIR "resources"
$BIN_DIR = Join-Path $RESOURCES_DIR "bin"

Write-Host "Fetching Node.js runtimes..." -ForegroundColor Green
Write-Host "Root directory: $ROOT" -ForegroundColor Yellow
Write-Host "Node version: $NodeVersion" -ForegroundColor Yellow

# Create bin directories
$WIN_BIN_DIR = Join-Path $BIN_DIR "win"

Write-Host "Creating binary directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $WIN_BIN_DIR | Out-Null

# Download Windows x64 Node.js runtime
$FileName = "node-v$NodeVersion-win-x64"
$Url = "https://nodejs.org/dist/v$NodeVersion/$FileName.zip"
$Archive = Join-Path $env:TEMP "$FileName.zip"

Write-Host "Downloading Windows x64 runtime..." -ForegroundColor Yellow
Write-Host "URL: $Url" -ForegroundColor Gray

try {
    Invoke-WebRequest -Uri $Url -OutFile $Archive -UseBasicParsing
    Write-Host "Downloaded: $Archive" -ForegroundColor Green
    
    # Extract ZIP
    Write-Host "Extracting ZIP archive..." -ForegroundColor Yellow
    Expand-Archive -Path $Archive -DestinationPath $env:TEMP -Force
    
    # Clean up extracted folder
    Remove-Item (Join-Path $env:TEMP $FileName) -Recurse -Force -ErrorAction SilentlyContinue
    
    # Clean up downloaded archive
    Remove-Item $Archive -Force -ErrorAction SilentlyContinue
    
} catch {
    Write-Host "Failed to download/extract Windows runtime: $_" -ForegroundColor Red
    throw
}

# Verify installation
Write-Host "`n=== Verifying installation ===" -ForegroundColor Cyan
$NodeExe = Join-Path $WIN_BIN_DIR "node.exe"
if (Test-Path $NodeExe) {
    Write-Host "✅ Node.js runtime installed at: $NodeExe" -ForegroundColor Green
    
    # Test the runtime
    $Version = & $NodeExe --version
    Write-Host "✅ Node.js version: $Version" -ForegroundColor Green
} else {
    throw "❌ Node.js runtime installation failed"
}

Write-Host "`n🎉 Node.js runtime fetch completed successfully!" -ForegroundColor Green
