param([switch]$Settings)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv and install requirements-tray.txt first.' }
$app = Join-Path $PSScriptRoot 'tray_app/app.py'
$arguments = '"' + $app + '"'
if ($Settings) { $arguments += ' --settings' }
Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
