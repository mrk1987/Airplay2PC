# Run offline regressions with generated logs outside the project root.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv and install requirements-windows.txt first.' }
$testLogs = Join-Path $projectRoot 'runtime/test-logs'
New-Item -ItemType Directory -Force -Path $testLogs | Out-Null
Push-Location $testLogs
try {
    & $python -m unittest discover -s (Join-Path $projectRoot 'tests') -v
    if ($LASTEXITCODE -ne 0) { throw "Tests exited with code $LASTEXITCODE" }
} finally { Pop-Location }
