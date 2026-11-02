param(
    [string]$NetInterface,
    [string]$Name = 'PC AirPlay',
    [switch]$ListInterfaces,
    [switch]$DebugLogging,
    [switch]$TimingDiagnostics,
    [ValidateRange(0,2000)][int]$OutputDelayMs = 0
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv with Python 3.12 and install requirements-windows.txt first.' }
$receiver = Join-Path $PSScriptRoot 'vendor/airplay2-receiver/ap2-receiver.py'
$previousPythonPath = $env:PYTHONPATH
$previousTimingLog = $env:AIRPLAY_TIMING_LOG_DIR
$previousOutputDelay = $env:AIRPLAY2PC_OUTPUT_DELAY_MS
$runtime = Join-Path $PSScriptRoot 'runtime'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Push-Location $runtime
try {
    $env:AIRPLAY2PC_OUTPUT_DELAY_MS = [string]$OutputDelayMs
    if ($TimingDiagnostics -or $OutputDelayMs -gt 0) {
        $env:PYTHONPATH = if ($previousPythonPath) { $PSScriptRoot + [IO.Path]::PathSeparator + $previousPythonPath } else { $PSScriptRoot }
    }
    if ($TimingDiagnostics) {
        $env:AIRPLAY_TIMING_LOG_DIR = Join-Path $PSScriptRoot 'runtime/timing'
        & $python -c 'from timing.clock import validate_clock; validate_clock()'
        if ($LASTEXITCODE -ne 0) { throw 'High-resolution timing clock validation failed.' }
    }
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
} finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
    $env:AIRPLAY_TIMING_LOG_DIR = $previousTimingLog
    $env:AIRPLAY2PC_OUTPUT_DELAY_MS = $previousOutputDelay
}
