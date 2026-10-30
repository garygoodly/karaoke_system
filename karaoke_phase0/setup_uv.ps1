#requires -Version 5.1
[CmdletBinding()]
param([switch]$SkipFFmpegCheck, [switch]$SkipMfaModels, [switch]$SkipMfa)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'

function Find-Exe([string]$Name, [string[]]$Candidates) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in $Candidates) { if ($p -and (Test-Path -LiteralPath $p -PathType Leaf)) { return $p } }
    return $null
}
function Invoke-Checked([string]$Executable, [string[]]$Argv) {
    Write-Host ('> ' + [IO.Path]::GetFileName($Executable) + ' ' + ($Argv -join ' ')) -ForegroundColor DarkGray
    # Windows PowerShell 5.1 can turn native stderr into a terminating
    # NativeCommandError when ErrorActionPreference=Stop. Exit code, not stderr,
    # determines success. Restore the caller's preference after the process.
    $priorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Executable @Argv
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $priorPreference
    }
    if ($exitCode -ne 0) { throw "Command failed ($exitCode): $Executable $($Argv -join ' ')" }
}
function Install-Winget([string]$Id) {
    $winget = Find-Exe 'winget' @()
    if (-not $winget) { throw "winget unavailable. Install $Id manually and rerun." }
    Invoke-Checked $winget @('install','--id',$Id,'-e','--accept-package-agreements','--accept-source-agreements')
}
function Find-Conda {
    $candidates = @(
        "$env:USERPROFILE\miniforge3\Scripts\conda.exe",
        "$env:USERPROFILE\Miniforge3\Scripts\conda.exe",
        "$env:LOCALAPPDATA\miniforge3\Scripts\conda.exe",
        "$env:ProgramData\miniforge3\Scripts\conda.exe"
    )
    $c = Find-Exe 'conda' $candidates
    if ($c) { return $c }
    $paths = @(Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Directory -ErrorAction SilentlyContinue | Where-Object Name -Match 'Miniforge')
    foreach ($p in $paths) {
        $found = Get-ChildItem $p.FullName -Filter conda.exe -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match '\\Scripts\\conda\.exe$' } | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}
function Check-Mfa([string]$Conda) {
    # Crucial: never invoke envs/karaoke-mfa/Scripts/mfa.exe directly on Windows.
    Invoke-Checked $Conda @('run','--no-capture-output','-n','karaoke-mfa','python','-c',"import soundfile as sf; print('SoundFile', sf.__version__, 'libsndfile', sf.__libsndfile_version__)")
    Invoke-Checked $Conda @('run','--no-capture-output','-n','karaoke-mfa','mfa','version')
}

Write-Host 'Karaoke Windows setup (uv + MFA)' -ForegroundColor Cyan
$uv = Find-Exe 'uv' @(
    "$env:LOCALAPPDATA\Microsoft\WinGet\Links\uv.exe",
    "$env:USERPROFILE\.local\bin\uv.exe",
    "$env:USERPROFILE\.cargo\bin\uv.exe"
)
if (-not $uv) {
    $pkg = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Directory -ErrorAction SilentlyContinue | Where-Object Name -Match '^astral-sh\.uv_' | Select-Object -First 1
    if ($pkg) { $uv = Find-Exe 'uv' @((Join-Path $pkg.FullName 'uv.exe')) }
}
if (-not $uv) {
    Install-Winget 'astral-sh.uv'
    $uv = Find-Exe 'uv' @("$env:LOCALAPPDATA\Microsoft\WinGet\Links\uv.exe")
    if (-not $uv) {
        $pkg = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Directory -ErrorAction SilentlyContinue | Where-Object Name -Match '^astral-sh\.uv_' | Select-Object -First 1
        if ($pkg) { $uv = Find-Exe 'uv' @((Join-Path $pkg.FullName 'uv.exe')) }
    }
}
if (-not $uv) { throw 'uv installed but executable not found. Restart Windows Terminal / IDE and rerun setup_uv.bat.' }
if (-not $SkipFFmpegCheck) {
    $ffmpeg = Find-Exe 'ffmpeg' @()
    $ffprobe = Find-Exe 'ffprobe' @()
    if (-not $ffmpeg -or -not $ffprobe) {
        Install-Winget 'Gyan.FFmpeg'
        $ffmpeg = Find-Exe 'ffmpeg' @()
        $ffprobe = Find-Exe 'ffprobe' @()
        if (-not $ffmpeg -or -not $ffprobe) { throw 'FFmpeg installed but not on current PATH. Restart terminal and rerun setup_uv.bat.' }
    }
}
if (-not (Test-Path -LiteralPath 'uv.lock')) { throw 'uv.lock missing: git pull the committed project before setup.' }
Invoke-Checked $uv @('sync','--locked','--python','3.11')
$verify = @'
import importlib
import torch, torchaudio, numpy
for n in ('torchcrepe','websockets','whisperx','demucs'):
    importlib.import_module(n)
print('Torch:',torch.__version__, 'Torchaudio:',torchaudio.__version__)
print('CUDA available:',torch.cuda.is_available())
print('Device:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')
'@
Invoke-Checked $uv @('run','--no-sync','python','-c',$verify)

if (-not $SkipMfa) {
    $conda = Find-Conda
    if (-not $conda) {
        Install-Winget 'CondaForge.Miniforge3'
        $conda = Find-Conda
    }
    if (-not $conda) { throw 'Miniforge installed but conda.exe not found. Restart terminal and rerun setup_uv.bat.' }
    $envNames = & $conda env list --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot query Conda environments.' }
    $existing = @($envNames.envs | Where-Object { (Split-Path $_ -Leaf) -eq 'karaoke-mfa' }).Count -gt 0
    if (-not $existing) {
        Invoke-Checked $conda @('create','-n','karaoke-mfa','-c','conda-forge','--override-channels','python=3.11','montreal-forced-aligner=3.4.3','libsndfile','pysoundfile','pip','-y')
    }
    # Verify existing environments rather than silently overwriting their dependencies.
    Check-Mfa $conda
    # Do not redirect stderr with 2>&1 under PowerShell 5.1 Stop preference.
    # Optional import may fail: its nonzero exit code is expected and triggers install.
    $priorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $conda run --no-capture-output -n karaoke-mfa python -c 'import spacy_pkuseg, dragonmapper, hanziconv'
        $extraExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $priorPreference
    }
    if ($extraExitCode -ne 0) {
        Write-Host 'Installing optional Mandarin tokenizer packages into MFA environment...' -ForegroundColor Yellow
        Invoke-Checked $conda @('run','--no-capture-output','-n','karaoke-mfa','python','-m','pip','install','spacy-pkuseg','dragonmapper','hanziconv')
        Check-Mfa $conda
        Invoke-Checked $conda @('run','--no-capture-output','-n','karaoke-mfa','python','-c','import spacy_pkuseg, dragonmapper, hanziconv')
    }
    if (-not $SkipMfaModels) {
        foreach ($model in @(@('acoustic','mandarin_mfa'),@('dictionary','mandarin_taiwan_mfa'),@('g2p','mandarin_taiwan_mfa'))) {
            Invoke-Checked $conda @('run','--no-capture-output','-n','karaoke-mfa','mfa','model','download',$model[0],$model[1],'--version','v3.0.0')
        }
    }
    Check-Mfa $conda
    Write-Host 'MFA verified via conda run (do not call mfa.exe directly).' -ForegroundColor Green
}
Write-Host 'Setup completed. GUI: .\run_gui_uv.ps1' -ForegroundColor Green
Write-Host 'Live pitch server: uv run --no-sync python .\tools\run_live_torchcrepe.py --device cpu' -ForegroundColor Cyan
Write-Host 'Note: CPU fallback refers to inference device; locked PyTorch wheels remain CUDA builds.' -ForegroundColor Yellow
