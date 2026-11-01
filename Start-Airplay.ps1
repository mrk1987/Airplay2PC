param(
    [string]$NetInterface,
    [string]$Name = 'PC AirPlay',
    [switch]$ListInterfaces,
    [switch]$DebugLogging
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv with Python 3.12 and install requirements-windows.txt first.' }
$receiver = Join-Path $PSScriptRoot 'vendor/airplay2-receiver/ap2-receiver.py'
$runtime = Join-Path $PSScriptRoot 'runtime'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Push-Location $runtime
try {
    if ($ListInterfaces) {
        & $python $receiver --list-interfaces
    } else {
        if (-not $NetInterface) { throw 'Pass -NetInterface with the GUID shown by -ListInterfaces.' }
        New-Item -ItemType Directory -Force pairings | Out-Null
        $receiverArgs = @($receiver, '-m', $Name, '-n', $NetInterface, '-ftor', '61')
        if ($DebugLogging) { $receiverArgs += '--debug' }
        & $python @receiverArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "Receiver exited with code $LASTEXITCODE" }
} finally { Pop-Location }
