@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_uv.ps1" %*
if errorlevel 1 (
  echo.
  echo SETUP FAILED. See the first error above. No project songs were deleted.
  pause
  exit /b 1
)
echo.
echo SETUP COMPLETE.
pause
