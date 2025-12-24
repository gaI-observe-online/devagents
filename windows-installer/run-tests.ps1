param(
  [switch]$CI
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# This test runner is intended for Windows machines (PowerShell 5.1 or pwsh).
# It installs Pester if missing and runs the installer regression tests.

if (-not (Get-Command Invoke-Pester -ErrorAction SilentlyContinue)) {
  Write-Host "Installing Pester..." -ForegroundColor Yellow
  try {
    Set-PSRepository -Name PSGallery -InstallationPolicy Trusted | Out-Null
  } catch {}
  Install-Module Pester -Force -Scope CurrentUser
}

$here = Split-Path -Parent $PSCommandPath
$tests = Join-Path $here "tests"

Invoke-Pester -Path $tests -CI:$CI

