@echo off
setlocal

REM GADOS installer bootstrapper (prevents running under the wrong interpreter).
REM Always launches Windows PowerShell (5.1) when available so the WPF UI works.

set SCRIPT_DIR=%~dp0
set PS1=%SCRIPT_DIR%install.ps1

where powershell.exe >nul 2>&1
if %errorlevel%==0 (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
  exit /b %errorlevel%
)

REM Fallback: PowerShell 7+ (no WPF UI). We force -NoUI for predictability.
where pwsh.exe >nul 2>&1
if %errorlevel%==0 (
  pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -NoUI %*
  exit /b %errorlevel%
)

echo ERROR: PowerShell is not available on this machine.
echo Install Windows PowerShell (5.1) or PowerShell 7 (pwsh) and retry.
exit /b 2

