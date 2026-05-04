@echo off
setlocal
set SCRIPT_DIR=%~dp0
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_windows.ps1" -InstallFFmpeg %*
if errorlevel 1 (
  echo.
  echo Install failed.
  exit /b 1
)
echo.
echo Install completed.
endlocal
