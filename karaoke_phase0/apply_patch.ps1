#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)] [string]$PatchZip,
    [switch]$RunTests,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$zip = (Resolve-Path -LiteralPath $PatchZip -ErrorAction Stop).Path
$protected = @('.git', 'songs', '.venv', '.venv-uv', 'patches', 'backups', 'benchmarks')
$allowedTop = @('src', 'tools', 'tests', 'README.md', '.gitignore', 'pyproject.toml', 'uv.lock', 'main.py', 'setup_uv.ps1', 'setup_uv.bat', 'run_gui_uv.ps1', 'apply_patch.ps1')
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$backupRoot = Join-Path ([System.IO.Path]::GetTempPath()) "karaoke_patch_backup_$([guid]::NewGuid().ToString('N'))"
$stage = Join-Path ([System.IO.Path]::GetTempPath()) "karaoke_patch_$([guid]::NewGuid().ToString('N'))"
$entries = @()
$changes = @()
try {
    if (-not (Test-Path -LiteralPath (Join-Path $root 'src\karaoke_phase0') -PathType Container)) { throw 'Run this script from the karaoke_phase0 project root (script must be stored there).' }
    if ([System.IO.Path]::GetExtension($zip).ToLowerInvariant() -ne '.zip') { throw 'Patch must be a ZIP.' }
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
    try {
        foreach ($e in $archive.Entries) {
            if ([string]::IsNullOrEmpty($e.Name)) { continue }
            $rel = $e.FullName.Replace('/', '\')
            $parts = $rel.Split('\')
            if ($rel.StartsWith('\') -or $rel -match '^[A-Za-z]:' -or $parts -contains '..' -or $parts -contains '.' -or $rel.Contains(':')) { throw "Unsafe ZIP entry: $rel" }
            if ($protected -contains $parts[0]) { throw "Protected path in patch: $rel" }
            if (($allowedTop -notcontains $parts[0]) -and ($parts.Count -ne 1 -or $rel -notmatch '^README_[A-Za-z0-9_-]+\.md$')) { throw "Unexpected patch path: $rel" }
            if ($parts[0] -in @('src','tools','tests') -and $parts.Count -lt 2) { throw "Unexpected root entry: $rel" }
            if ($entries | Where-Object { $_.rel -eq $rel }) { throw "Duplicate ZIP entry: $rel" }
            $entries += [pscustomobject]@{ rel=$rel; entry=$e }
        }
        if ($entries.Count -eq 0) { throw 'ZIP contains no files.' }
        $git = Get-Command git -ErrorAction SilentlyContinue
        if ($git -and (Test-Path -LiteralPath (Join-Path $root '.git'))) {
            $dirty = & git -C $root status --porcelain --untracked-files=no 2>$null
            if ($LASTEXITCODE -eq 0 -and $dirty -and -not $Force) { throw 'Tracked Git changes detected. Commit or stash first, or use -Force after reviewing them.' }
        }
        if ($git -and (Test-Path -LiteralPath (Join-Path $root '.git')) -and -not $Force) {
            foreach ($item in $entries) {
                $dest = Join-Path $root $item.rel
                if (Test-Path -LiteralPath $dest) {
                    $tracked = & git -C $root ls-files --error-unmatch -- $item.rel.Replace('\','/') 2>$null
                    if ($LASTEXITCODE -ne 0) { throw "Existing untracked file would be overwritten: $($item.rel). Commit it first or review -Force." }
                }
            }
        }
        Write-Host "Patch: $zip"
        foreach ($item in $entries) {
            $dest = Join-Path $root $item.rel
            $mode = if (Test-Path -LiteralPath $dest) { 'REPLACE' } else { 'ADD' }
            Write-Host "$mode  $($item.rel)"
            $changes += [pscustomobject]@{ rel=$item.rel; dest=$dest; existed=(Test-Path -LiteralPath $dest) }
        }
        # Proceed automatically after path and Git checks.
        New-Item -ItemType Directory -Path $stage -Force | Out-Null
        foreach ($item in $entries) {
            $out = Join-Path $stage $item.rel
            New-Item -ItemType Directory -Path (Split-Path $out -Parent) -Force | Out-Null
            $stream = [System.IO.File]::Create($out)
            try { $inputStream = $item.entry.Open(); try { $inputStream.CopyTo($stream) } finally { $inputStream.Dispose() } } finally { $stream.Dispose() }
        }
        foreach ($c in $changes) {
            if ($c.existed) {
                $back = Join-Path $backupRoot $c.rel
                New-Item -ItemType Directory -Path (Split-Path $back -Parent) -Force | Out-Null
                Copy-Item -LiteralPath $c.dest -Destination $back -Force
            }
        }
        $applied = @()
        try {
            foreach ($c in $changes) {
                $source = Join-Path $stage $c.rel
                New-Item -ItemType Directory -Path (Split-Path $c.dest -Parent) -Force | Out-Null
                Copy-Item -LiteralPath $source -Destination $c.dest -Force
                $applied += $c
            }
        } catch {
            foreach ($c in $applied) {
                if ($c.existed) { Copy-Item -LiteralPath (Join-Path $backupRoot $c.rel) -Destination $c.dest -Force }
                else { Remove-Item -LiteralPath $c.dest -Force }
            }
            throw
        }
        Write-Host "Applied $($changes.Count) file(s). Temporary rollback copies will be removed on exit."
        if ($RunTests) {
            $env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
            $env:PYTHONPATH = Join-Path $root 'src'
            Push-Location $root
            try { & uv run --no-sync python -m pytest -q; if ($LASTEXITCODE -ne 0) { Write-Warning 'Tests failed. Patch is still applied; restore backed-up files or use Git to revert after review.' } }
            finally { Pop-Location }
        } else { Write-Host 'Tests not run. Add -RunTests to run pytest.' }
    } finally { $archive.Dispose() }
} finally { if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }; if (Test-Path -LiteralPath $backupRoot) { Remove-Item -LiteralPath $backupRoot -Recurse -Force } }
