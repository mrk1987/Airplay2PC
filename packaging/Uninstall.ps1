$ErrorActionPreference = 'Stop'
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $env:PSModulePath
$root = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent)).TrimEnd('\')
$marker = Join-Path $root 'installation.json'
if (-not (Test-Path -LiteralPath $marker)) { throw 'Installation marker missing; nothing removed.' }
$installed = Get-Content -Raw -LiteralPath $marker | ConvertFrom-Json
if ($installed.root -ne $root -or (Split-Path $root -Leaf) -ne 'Airplay2PC') {
    throw 'Installation path validation failed; nothing removed.'
}
# Check every ancestor before recursive removal, including any junctions.
$check = Get-Item -LiteralPath $root
while ($check) {
    if ($check.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Refusing to uninstall through a reparse point.' }
    $check = $check.Parent
}
$running = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -and $_.CommandLine.Contains($root + '\')
})
if ($running.Count) { throw 'Quit Airplay2PC and stop its receiver before uninstalling.' }
if ((Read-Host 'Remove Airplay2PC? Pairings, settings and logs will be kept. Type YES') -cne 'YES') { exit }
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Programs')) 'Airplay2PC.lnk'
if (Test-Path -LiteralPath $shortcutPath) {
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
    if ($shortcut.TargetPath -eq (Join-Path $root '.venv\Scripts\pythonw.exe')) { Remove-Item -LiteralPath $shortcutPath }
}
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$startup = Get-ItemProperty -LiteralPath $runKey -Name Airplay2PC -ErrorAction SilentlyContinue
if ($startup -and $startup.Airplay2PC.Contains($root + '\')) {
    Remove-ItemProperty -LiteralPath $runKey -Name Airplay2PC
}
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Airplay2PC'
$entry = Get-ItemProperty -LiteralPath $uninstallKey -ErrorAction SilentlyContinue
if ($entry -and $entry.InstallLocation -eq $root) { Remove-Item -LiteralPath $uninstallKey }
$targets = @(Get-ChildItem -LiteralPath $root -Force | Where-Object Name -ne 'runtime')
foreach ($target in $targets) {
    $resolved = [IO.Path]::GetFullPath($target.FullName)
    if (-not $resolved.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Removal path escaped the installation.' }
    if ($target.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Refusing to remove a reparse point.' }
}
foreach ($target in $targets) { Remove-Item -LiteralPath $target.FullName -Recurse -Force }
Write-Host "Removed Airplay2PC. Your data remains in $root\runtime."
