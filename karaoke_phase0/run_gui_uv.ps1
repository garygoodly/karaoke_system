$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
if (-not (Test-Path '.venv-uv\Scripts\python.exe')) {
    throw 'Run .\setup_uv.ps1 first.'
}
& uv run --no-sync python main.py gui
if ($LASTEXITCODE -ne 0) { throw "GUI exited with code $LASTEXITCODE" }
