[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Input,
    [Parameter(Mandatory = $true)]
    [string]$SongId,
    [Parameter(Mandatory = $true)]
    [string]$Title,
    [ValidateSet("en", "ja", "zh")]
    [string]$Language = "ja",
    [string]$OutputDir = ".\songs",
    [string]$LyricsFile = "",
    [string]$LyricsUrl = "",
    [string]$KaraokeAudio = "",
    [switch]$UseDemucs,
    [ValidateSet("heuristic", "whisperx", "mfa")]
    [string]$Aligner = "heuristic",
    [string]$WhisperXModel = "small",
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

if ((-not $LyricsFile) -and (-not $LyricsUrl)) {
    throw "Provide either -LyricsFile or -LyricsUrl for subtitle-first preprocessing."
}

$CmdArgs = @(
    "-m", "karaoke_system.pipeline.preprocess_song",
    "--input", (Resolve-Path $Input),
    "--song-id", $SongId,
    "--title", $Title,
    "--language", $Language,
    "--output-dir", $OutputDir,
    "--aligner", $Aligner,
    "--whisperx-model", $WhisperXModel
)

if ($LyricsFile) {
    $CmdArgs += @("--lyrics-file", (Resolve-Path $LyricsFile))
}
if ($LyricsUrl) {
    $CmdArgs += @("--lyrics-url", $LyricsUrl)
}
if ($KaraokeAudio) {
    $CmdArgs += @("--karaoke-audio", (Resolve-Path $KaraokeAudio))
}
if ($UseDemucs) {
    $CmdArgs += "--use-demucs"
}

& $Python @CmdArgs
if ($LASTEXITCODE -ne 0) {
    throw "Preprocess step failed"
}

if ($BuildCache) {
    $SongDir = Join-Path $OutputDir $SongId
    & $Python (Join-Path $RepoRoot "scripts\build_playback_cache.py") --song-dir $SongDir --keys $WarmupKeys
    if ($LASTEXITCODE -ne 0) {
        throw "Playback cache build failed"
    }
}
