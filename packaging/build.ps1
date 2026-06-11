# Build DeveloperOS.exe (desktop ladder step C, D-0031).
# PyInstaller is a dev-time dependency only; the runtime stays stdlib-only.
# Usage:  cd packaging; ./build.ps1     -> dist/DeveloperOS.exe
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m PyInstaller --version *> $null
if (-not $?) {
    Write-Host "PyInstaller not found - installing (dev-time only)..."
    python -m pip install pyinstaller
}

python -m PyInstaller --noconfirm --clean devos.spec

$exe = Join-Path $PSScriptRoot "dist\DeveloperOS.exe"
if (Test-Path $exe) {
    Write-Host "OK: $exe"
    Write-Host ("Size: {0:N1} MB" -f ((Get-Item $exe).Length / 1MB))
} else {
    throw "Build finished but $exe was not produced."
}
