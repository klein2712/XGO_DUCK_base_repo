# Start the XGO Duck walking policy in the MuJoCo viewer.
# Any extra arguments are passed through, e.g.:
#   .\simulation\windows\run_walk.ps1 --policy getup
#   .\simulation\windows\run_walk.ps1 --vx 0.15 --headless --duration 10
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { Write-Error "Run simulation\windows\setup.ps1 first." }

& $Python (Join-Path $RepoRoot "simulation\common\xgoduck_sim2sim.py") @args
exit $LASTEXITCODE
