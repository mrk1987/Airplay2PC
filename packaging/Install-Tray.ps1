param(
    [switch]$Launch,
    [string]$ShortcutPath = (Join-Path ([Environment]::GetFolderPath('Programs')) 'Airplay2PC.lnk')
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $env:PSModulePath
$python = Join-Path $projectRoot '.venv/Scripts/pythonw.exe'
$app = Join-Path $projectRoot 'tray_app/app.py'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install requirements-tray.txt into .venv first.' }
$path = [IO.Path]::GetFullPath($ShortcutPath)
$icon = Join-Path $projectRoot 'assets/icons/Airplay2PC-logo.ico'
if (-not (Test-Path -LiteralPath $icon)) { throw 'The Airplay2PC icon is missing.' }
if (-not ('Airplay2PCShortcutNative' -as [type])) {
    Add-Type -TypeDefinition 'using System; using System.Text; using System.Runtime.InteropServices; public static class Airplay2PCShortcutNative { [DllImport("shell32.dll", CharSet=CharSet.Unicode)] public static extern void SHChangeNotify(uint events, uint flags, string item1, IntPtr item2); [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern uint GetLongPathName(string path, StringBuilder result, uint length); }'
}
function Get-CanonicalShortcutPath([string]$Value) {
    $buffer = New-Object Text.StringBuilder 32768
    $length = [Airplay2PCShortcutNative]::GetLongPathName($Value, $buffer, $buffer.Capacity)
    if ($length -eq 0 -or $length -ge $buffer.Capacity) { throw 'Cannot resolve the existing shortcut path.' }
    return [IO.Path]::GetFullPath($buffer.ToString())
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($path)
if ((Test-Path -LiteralPath $path) -and $shortcut.TargetPath -and $shortcut.TargetPath -ne $python) {
    $oldRoot = Split-Path (Split-Path (Split-Path $shortcut.TargetPath -Parent) -Parent) -Parent
    $oldPython = Join-Path $oldRoot '.venv/Scripts/pythonw.exe'
    $oldApp = Join-Path $oldRoot 'tray_app/app.py'
    $argumentMatch = [regex]::Match($shortcut.Arguments, '^"(?<app>[^"]+)"$')
    if (-not $argumentMatch.Success -or -not (Test-Path -LiteralPath $oldApp) -or
        -not (Test-Path -LiteralPath $oldPython) -or
        -not (Test-Path -LiteralPath $argumentMatch.Groups['app'].Value)) {
        throw 'An unrelated shortcut exists at this path; it was not overwritten.'
    }
    if ((Get-CanonicalShortcutPath $shortcut.TargetPath) -ne (Get-CanonicalShortcutPath $oldPython) -or
        (Get-CanonicalShortcutPath $argumentMatch.Groups['app'].Value) -ne (Get-CanonicalShortcutPath $oldApp)) {
        throw 'An unrelated shortcut exists at this path; it was not overwritten.'
    }
}
$shortcut.TargetPath = $python
$shortcut.Arguments = '"' + $app + '"'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = $icon + ',0'
$shortcut.Description = 'AirPlay receiver controls and settings'
$shortcut.WindowStyle = 7
$shortcut.Save()
# Ask the shell to refresh this item without restarting Explorer or clearing caches.
[Airplay2PCShortcutNative]::SHChangeNotify(0x2000, 0x0005, $path, [IntPtr]::Zero)
Write-Output "Start menu shortcut: $path"
if ($Launch) { & (Join-Path $projectRoot 'packaging/Start-Tray.ps1') }
