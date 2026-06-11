# Build the DeveloperOS Windows installer (desktop ladder step D, D-0032).
# Usage:  cd packaging; ./build_installer.ps1
#   -> dist/DeveloperOS-Setup-<version>.exe
# Inno Setup is a DEV-TIME tool only (like PyInstaller); the runtime stays stdlib-only.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Version from the single source of truth (devos/__init__.py).
$initText = Get-Content ..\devos\__init__.py -Raw
if ($initText -notmatch '__version__\s*=\s*"([^"]+)"') { throw "Could not read devos.__version__" }
$version = $Matches[1]
Write-Host "Building installer for DeveloperOS $version"

# Ensure the packaged exe exists (build it if needed).
if (-not (Test-Path .\dist\DeveloperOS.exe)) {
    Write-Host "dist\DeveloperOS.exe missing - building it first..."
    ./build.ps1
}

# Locate Inno Setup's command-line compiler.
$candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup not found. Install it (dev-time only) with:  winget install JRSoftware.InnoSetup"
}

& $iscc "/DMyAppVersion=$version" installer.iss
$setup = Join-Path $PSScriptRoot "dist\DeveloperOS-Setup-$version.exe"
if (Test-Path $setup) {
    Write-Host "OK: $setup"
    Write-Host ("Size: {0:N1} MB" -f ((Get-Item $setup).Length / 1MB))
} else {
    throw "ISCC finished but $setup was not produced."
}
