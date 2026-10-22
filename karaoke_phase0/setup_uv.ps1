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
Write-Host 'Resolving CUDA 12.8 PyTorch + Demucs + WhisperX for Python 3.11...' -ForegroundColor Cyan
if (Test-Path 'uv.lock') {
    Run-Uv @('sync','--locked','--python','3.11')
} else {
    Run-Uv @('lock','--python','3.11')
    Run-Uv @('sync','--locked','--python','3.11')
}
Run-Uv @('run','--no-sync','python','-c',"import torch, torchaudio, whisperx, demucs, numpy; print('Torch:',torch.__version__); print('CUDA:',torch.cuda.is_available()); print('NumPy:',numpy.__version__); print('GPU:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Unavailable'); assert torch.cuda.is_available(), 'CUDA PyTorch unavailable'")
Write-Host 'Environment ready. Launch GUI: .\run_gui_uv.ps1' -ForegroundColor Green
