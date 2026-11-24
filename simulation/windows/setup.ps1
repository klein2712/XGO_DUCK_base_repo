# XGO Duck simulation - Windows setup (MuJoCo CPU + ONNX policies)
# Usage (from the repo root, in PowerShell):
#   powershell -ExecutionPolicy Bypass -File simulation\windows\setup.ps1
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Venv = Join-Path $RepoRoot ".venv"
$Common = Join-Path $RepoRoot "simulation\common"

# 1) Find Python 3.12+ (prefer 3.12, same version as the training repo)
$py = $null
foreach ($v in @("3.12", "3.13", "3.14")) {
    try { & py "-$v" -c "import sys" 2>$null; if ($LASTEXITCODE -eq 0) { $py = @("py", "-$v"); break } } catch {}
}
if (-not $py) {
    Write-Error "Python 3.12+ not found. Install it from https://www.python.org/downloads/windows/ (tick 'Add to PATH')."
}
Write-Host "Using Python: $($py -join ' ')"

# 2) Virtual environment in <repo>\.venv
if (-not (Test-Path $Venv)) {
    & $py[0] $py[1] -m venv $Venv
}
$Python = Join-Path $Venv "Scripts\python.exe"

# 3) Dependencies
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Common "requirements.txt")

# 4) Robot model + pretrained policies
& $Python (Join-Path $Common "fetch_assets.py")

Write-Host ""
Write-Host "Setup complete. Start the walking demo with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File simulation\windows\run_walk.ps1"
