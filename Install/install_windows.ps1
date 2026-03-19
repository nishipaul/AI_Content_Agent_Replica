# Install script for Windows – ensures Python 3.12+, uv, and project .venv are ready.
# Run from PowerShell (e.g. right-click Install\install_windows.ps1 -> Run with PowerShell).
# Repo root is inferred from this script's location.

$ErrorActionPreference = "Stop"
$MIN_MAJOR = 3
$MIN_MINOR = 12

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

Write-Host "==> Repo root: $RepoRoot"
Set-Location $RepoRoot

# --- Check Python 3.12+ ---
function Get-PythonPath {
  $candidates = @("python3.12", "python")
  foreach ($cmd in $candidates) {
    try {
      $p = Get-Command $cmd -ErrorAction SilentlyContinue
      if (-not $p) { continue }
      $out = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
      if (-not $out) { continue }
      $parts = $out.Trim().Split(".")
      $major = [int]$parts[0]
      $minor = [int]$parts[1]
      if ($major -ge $MIN_MAJOR -and $minor -ge $MIN_MINOR) {
        return $p.Source
      }
    } catch {
      continue
    }
  }
  return $null
}

$PythonExe = Get-PythonPath
if (-not $PythonExe) {
  Write-Host "ERROR: Python $MIN_MAJOR.$MIN_MINOR or higher is required."
  Write-Host "Install from https://www.python.org/downloads/ or: winget install Python.Python.3.12"
  exit 1
}

Write-Host "==> Using Python: $(& $PythonExe --version)"

# --- Ensure uv on PATH (common install locations) ---
$uvPaths = @(
  "$env:USERPROFILE\.local\bin",
  "$env:USERPROFILE\.cargo\bin",
  "$env:LOCALAPPDATA\Programs\uv\uv.exe"
)
foreach ($p in $uvPaths) {
  if ($p -like "*\uv.exe") {
    if (Test-Path $p) { $env:PATH = "$(Split-Path $p);$env:PATH"; break }
  } else {
    $uvExe = Join-Path $p "uv.exe"
    if (Test-Path $uvExe) { $env:PATH = "$p;$env:PATH"; break }
  }
}

# --- Install uv if missing ---
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "==> Installing uv..."
  Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
  Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing | Invoke-Expression
  $env:PATH = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: uv was installed but not found. Close and reopen PowerShell, then re-run this script."
    exit 1
  }
} else {
  Write-Host "==> uv already installed: $(uv --version)"
}

# --- Create .venv and install dependencies ---
Write-Host "==> Creating .venv and syncing dependencies with uv..."
uv sync --frozen

Write-Host ""
Write-Host "==> Install complete."
Write-Host "    Activate the environment:  .venv\Scripts\Activate.ps1"
Write-Host "    Run the API server:        uv run uvicorn agent.api:app --host 0.0.0.0 --port 5000"
Write-Host "    Or from repo root:         uv run run_api"
