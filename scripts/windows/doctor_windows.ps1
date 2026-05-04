[CmdletBinding()]
param(
    [string]$VenvDir = ".venv",
    [string]$SongDir = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
$Python = Join-Path $RepoRoot "$VenvDir\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run scripts\\windows\\install_windows.ps1 first."
}

$Args = @((Join-Path $RepoRoot "scripts\doctor.py"))
if ($SongDir) {
    $Args += @("--song-dir", (Resolve-Path $SongDir))
}

& $Python @Args
