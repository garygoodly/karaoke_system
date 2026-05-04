[CmdletBinding()]
param(
    [string]$PythonCommand = "",
    [string]$VenvDir = ".venv",
    [switch]$InstallFFmpeg,
    [switch]$InstallOptionalPythonPackages,
    [switch]$SkipDoctor
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Resolve-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
}

function Get-PythonCommand {
    param([string]$Requested)

    if ($Requested) {
        return $Requested
    }

    $candidates = @(
        "py -3.12",
        "py -3.11",
        "py",
        "python"
    )

    foreach ($candidate in $candidates) {
        try {
            & cmd /c "$candidate --version" *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
        catch {
        }
    }

    throw "Python 3.11+ was not found. Install Python first, then rerun this script."
}

function Invoke-CmdLine {
    param(
        [string]$CommandLine,
        [string]$WorkingDirectory
    )

    Push-Location $WorkingDirectory
    try {
        & cmd /c $CommandLine
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $CommandLine"
        }
    }
    finally {
        Pop-Location
    }
}

$RepoRoot = Resolve-RepoRoot
$Python = Get-PythonCommand -Requested $PythonCommand
$VenvPath = Join-Path $RepoRoot $VenvDir
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

Write-Step "Repository root: $RepoRoot"
Write-Step "Using Python command: $Python"

if (-not (Test-Path $VenvPython)) {
    Write-Step "Creating virtual environment"
    Invoke-CmdLine -CommandLine "$Python -m venv `"$VenvPath`"" -WorkingDirectory $RepoRoot
}
else {
    Write-Step "Virtual environment already exists"
}

Write-Step "Upgrading pip tooling"
& $VenvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip tooling"
}

Write-Step "Installing Windows base requirements"
& $VenvPython -m pip install -r (Join-Path $RepoRoot "requirements-windows.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install base requirements"
}

if ($InstallOptionalPythonPackages) {
    Write-Step "Installing optional Python packages"
    Get-Content (Join-Path $RepoRoot "requirements-windows-optional.txt") |
        Where-Object { $_.Trim() -and -not $_.Trim().StartsWith("#") } |
        ForEach-Object {
            $package = $_.Trim()
            Write-Host "Trying optional package: $package" -ForegroundColor Yellow
            & $VenvPython -m pip install $package
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Optional package failed and was skipped: $package"
            }
        }
}

if ($InstallFFmpeg) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Step "Installing FFmpeg with winget"
        & winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "winget FFmpeg install did not complete successfully. You can install FFmpeg manually later."
        }
    }
    else {
        Write-Warning "winget is not available. Install FFmpeg manually and ensure ffmpeg.exe / ffprobe.exe are in PATH."
    }
}

if (-not $SkipDoctor) {
    Write-Step "Running environment doctor"
    & $VenvPython (Join-Path $RepoRoot "scripts\doctor.py")
}

Write-Host "`nWindows setup finished." -ForegroundColor Green
Write-Host "Launch the player with:" -ForegroundColor Green
Write-Host ".\scripts\windows\start_player.ps1 -SongDir .\songs\my_song" -ForegroundColor Green
