@echo off
setlocal
set SCRIPT_DIR=%~dp0
if "%~1"=="" (
  echo Usage: start_player.bat ^<song_dir^>
  exit /b 1
)
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start_player.ps1" -SongDir "%~1"
endlocal
