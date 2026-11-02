param([switch]$Launch)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv/Scripts/pythonw.exe'
$app = Join-Path $PSScriptRoot 'tray_app/app.py'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install requirements-tray.txt into .venv first.' }
$path = Join-Path ([Environment]::GetFolderPath('Programs')) 'Airplay2PC.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($path)
if ((Test-Path -LiteralPath $path) -and $shortcut.TargetPath -and $shortcut.TargetPath -ne $python) {
    throw 'A different Airplay2PC shortcut exists; it was not overwritten.'
}
$shortcut.TargetPath = $python
$shortcut.Arguments = '"' + $app + '"'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = (Join-Path $PSScriptRoot 'assets/icons/Airplay2PC-logo.ico') + ',0'
$shortcut.Description = 'AirPlay receiver controls and settings'
$shortcut.WindowStyle = 7
$shortcut.Save()
Write-Output "Start menu shortcut: $path"
if ($Launch) { & (Join-Path $PSScriptRoot 'Start-Tray.ps1') }
