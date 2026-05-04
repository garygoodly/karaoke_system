[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SongDir,
    [string]$VenvDir = ".venv",
    [switch]$BuildCache,
    [int[]]$WarmupKeys = @(0)
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
$Python = Join-Path $RepoRoot "$VenvDir\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run scripts\\windows\\install_windows.ps1 first."
}

$SongDirResolved = (Resolve-Path $SongDir)
$Manifest = Join-Path $SongDirResolved "manifest.json"
if (-not (Test-Path $Manifest)) {
    throw "manifest.json not found in $SongDirResolved"
}

$CacheDir = Join-Path $SongDirResolved "cache"
$NeedsCache = $BuildCache
if (-not $NeedsCache) {
    $Expected = @(
        (Join-Path $CacheDir "playback_original_+0.mp4"),
        (Join-Path $CacheDir "playback_karaoke_+0.mp4")
    )
    $Missing = $Expected | Where-Object { -not (Test-Path $_) }
    if ($Missing.Count -gt 0) {
        $NeedsCache = $true
    }
}

if ($NeedsCache) {
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        throw "Playback cache is missing and ffmpeg is not in PATH. Run install_windows.ps1 -InstallFFmpeg first."
    }
    Write-Host "Building playback cache..." -ForegroundColor Cyan
    & $Python (Join-Path $RepoRoot "scripts\build_playback_cache.py") --song-dir $SongDirResolved --keys $WarmupKeys
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build playback cache"
    }
}

& $Python (Join-Path $RepoRoot "app.py") --song-dir $SongDirResolved
