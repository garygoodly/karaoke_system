param([switch]$SkipFFmpegCheck)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'

function Run-Uv([string[]]$Arguments) {
    & uv @Arguments
    if ($LASTEXITCODE -ne 0) { throw "uv failed ($LASTEXITCODE): $($Arguments -join ' ')" }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv not found. Install with: winget install --id astral-sh.uv -e ; reopen terminal and rerun.'
}
if (-not $SkipFFmpegCheck) {
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
        throw 'FFmpeg and ffprobe must be on PATH. Install with: winget install --id Gyan.FFmpeg -e ; reopen terminal.'
    }
}
if (-not (Test-Path 'uv.lock')) {
    throw 'uv.lock not found. Pull the committed lockfile before installing.'
}
Write-Host 'Installing locked Karaoke dependencies for Python 3.11...' -ForegroundColor Cyan
Write-Host 'Note: current uv.lock uses CUDA 12.8 PyTorch wheels, even when running on CPU.' -ForegroundColor Yellow
Run-Uv @('sync','--locked','--python','3.11')
$check = @'
import importlib
import torch
import torchaudio
import numpy
for name in ('torchcrepe', 'websockets', 'whisperx', 'demucs'):
    importlib.import_module(name)
print('Torch:', torch.__version__)
print('Torchaudio:', torchaudio.__version__)
print('NumPy:', numpy.__version__)
print('CUDA available:', torch.cuda.is_available())
print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')
'@
Run-Uv @('run','--no-sync','python','-c',$check)
Write-Host 'Environment ready. Launch GUI: .\run_gui_uv.ps1' -ForegroundColor Green
Write-Host 'For live pitch, start: uv run --no-sync python .\tools\run_live_torchcrepe.py --device cpu' -ForegroundColor Cyan
