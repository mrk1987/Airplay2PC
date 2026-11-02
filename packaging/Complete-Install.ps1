param(
    [Parameter(Mandatory=$true)][string]$InstallDirectory,
    [Parameter(Mandatory=$true)][string]$Version,
    [switch]$NoShortcut
)
$ErrorActionPreference = 'Stop'
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $env:PSModulePath
$installRoot = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
foreach ($required in @('.venv/Scripts/python.exe','tray_app/app.py','packaging/Start-Tray.ps1','assets/icons/Airplay2PC-logo.ico')) {
    if (-not (Test-Path -LiteralPath (Join-Path $installRoot $required))) { throw "Incomplete installation: $required" }
}
if (-not $NoShortcut) {
    & (Join-Path $installRoot 'packaging/Install-Tray.ps1')
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Airplay2PC'
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -Path $key -Name DisplayName -Value 'Airplay2PC' -Force | Out-Null
    New-ItemProperty -Path $key -Name DisplayVersion -Value $Version -Force | Out-Null
    New-ItemProperty -Path $key -Name Publisher -Value 'mrk1987' -Force | Out-Null
    New-ItemProperty -Path $key -Name InstallLocation -Value $installRoot -Force | Out-Null
    New-ItemProperty -Path $key -Name DisplayIcon -Value (Join-Path $installRoot 'assets/icons/Airplay2PC-logo.ico') -Force | Out-Null
    $uninstall = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $installRoot 'packaging/Uninstall.ps1') + '"'
    New-ItemProperty -Path $key -Name UninstallString -Value $uninstall -Force | Out-Null
    New-ItemProperty -Path $key -Name NoModify -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $key -Name NoRepair -Value 1 -PropertyType DWord -Force | Out-Null
}
$work = Join-Path $installRoot '.setup'
if (Test-Path -LiteralPath $work) {
    $checkedWork = [IO.Path]::GetFullPath($work)
    if ((Split-Path $checkedWork -Parent) -ne $installRoot -or (Split-Path $checkedWork -Leaf) -ne '.setup' -or
        ((Get-Item -LiteralPath $checkedWork).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Setup cleanup path validation failed.'
    }
    Remove-Item -LiteralPath $checkedWork -Recurse -Force
}
@{version=$Version; root=$installRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $installRoot 'installation.json') -Encoding UTF8
