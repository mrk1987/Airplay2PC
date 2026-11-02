param([switch]$Settings)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv and install requirements-tray.txt first.' }
$app = Join-Path $projectRoot 'tray_app/app.py'
$arguments = '"' + $app + '"'
if ($Settings) { $arguments += ' --settings' }
Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden
