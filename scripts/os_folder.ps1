#!/usr/bin/env pwsh
# PowerShell equivalent of os_folder.sh
# Returns the appropriate OS folder name for the current platform

$OS = [System.Environment]::OSVersion.Platform
$Architecture = [System.Environment]::Is64BitOperatingSystem

if ($IsWindows -or $OS -eq "Win32NT") {
    Write-Output "win"
} elseif ($IsLinux -or $OS -eq "Unix") {
    $UnameM = uname -m
    if ($UnameM -eq "x86_64") {
        Write-Output "linux"
    } else {
        Write-Output "unsupported"
        exit 1
    }
} elseif ($IsMacOS -or $OS -eq "Darwin") {
    $UnameM = uname -m
    if ($UnameM -eq "arm64") {
        Write-Output "mac-arm64"
    } else {
        Write-Output "mac-x64"
    }
} else {
    Write-Output "unsupported"
    exit 1
}
