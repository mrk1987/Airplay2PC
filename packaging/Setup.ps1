param(
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'Programs\Airplay2PC'),
    [switch]$NoShortcut,
    [switch]$NoLaunch
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# A parent PowerShell 7 process can pass its module path to Windows PowerShell.
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $env:PSModulePath

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}
function Get-Verified([string]$Url, [string]$Path, [string]$Sha256) {
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Path
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ne $Sha256) {
        throw "Download checksum mismatch: $Url"
    }
}

try {
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
        throw 'Airplay2PC 0.1 requires Windows x64 (Intel or AMD).'
    }
    $installRoot = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
    if (Test-Path -LiteralPath $installRoot) {
        # A previous uninstall may have retained pairings and settings.
        $unexpected = @(Get-ChildItem -LiteralPath $installRoot -Force | Where-Object Name -ne 'runtime')
        if ($unexpected.Count) { throw 'The destination is not empty. Quit and uninstall the previous version first, or choose another directory.' }
    }
    Write-Host 'Airplay2PC 0.1 setup'
    Write-Host "Destination: $installRoot"
    Write-Host 'Setup downloads Python, dependencies and the experimental upstream receiver.'
    Write-Host 'The upstream receiver has no licence file; see THIRD_PARTY.md for details.'
    New-Item -ItemType Directory -Force -Path $installRoot | Out-Null
    $work = Join-Path $installRoot '.setup'
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') | ConvertFrom-Json
    $payload = Join-Path $PSScriptRoot 'payload.zip'
    if ((Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash -ne $manifest.payload_sha256) {
        throw 'Installer payload checksum mismatch.'
    }
    Copy-Item -LiteralPath $payload -Destination (Join-Path $work 'payload.zip')
    Expand-Archive -LiteralPath (Join-Path $work 'payload.zip') -DestinationPath $installRoot

    Write-Host 'Downloading the setup tool...'
    Get-Verified 'https://github.com/astral-sh/uv/releases/download/0.12.15/uv-x86_64-pc-windows-msvc.zip' (Join-Path $work 'uv.zip') '477bd99a84e34891f2bd4c9152ddeb74e971accccbc59c0f0301f11f08a32d46'
    Expand-Archive -LiteralPath (Join-Path $work 'uv.zip') -DestinationPath (Join-Path $work 'uv')
    $uv = Join-Path $work 'uv\uv.exe'
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $installRoot 'python'
    $env:UV_CACHE_DIR = Join-Path $work 'cache'
    $env:UV_PYTHON_PREFERENCE = 'only-managed'
    Write-Host 'Installing a private Python runtime...'
    Invoke-Checked $uv @('python', 'install', '3.12.12', '--no-bin')
    Invoke-Checked $uv @('venv', '--python', '3.12.12', (Join-Path $installRoot '.venv'))
    $python = Join-Path $installRoot '.venv\Scripts\python.exe'
    Write-Host 'Installing the pinned Python packages...'
    Invoke-Checked $uv @('pip', 'install', '--python', $python, '--require-hashes', '--only-binary', 'netifaces', '--find-links', (Join-Path $installRoot 'wheels'), '-r', (Join-Path $installRoot 'requirements-release.txt'))

    Write-Host 'Downloading the pinned upstream receiver...'
    Get-Verified 'https://codeload.github.com/openairplay/airplay2-receiver/zip/6c343d3679ddb561c61566985acaaf587d0a3bd3' (Join-Path $work 'receiver.zip') 'b35d21ef303bcc7788cfcbb57e3df7fec12566d39601ed3471b94e73b4953a1c'
    Expand-Archive -LiteralPath (Join-Path $work 'receiver.zip') -DestinationPath (Join-Path $work 'upstream')
    $vendor = Join-Path $installRoot 'vendor'
    New-Item -ItemType Directory -Force -Path $vendor | Out-Null
    $receiver = Join-Path $vendor 'airplay2-receiver'
    Move-Item -LiteralPath (Join-Path $work 'upstream\airplay2-receiver-6c343d3679ddb561c61566985acaaf587d0a3bd3') -Destination $receiver
    Invoke-Checked $python @((Join-Path $installRoot 'packaging\apply_patches.py'), $receiver,
        (Join-Path $installRoot 'patches\windows-playback.patch'),
        (Join-Path $installRoot 'patches\timing-diagnostics.patch'),
        (Join-Path $installRoot 'patches\output-delay.patch'),
        (Join-Path $installRoot 'patches\network-discovery.patch'))
    Invoke-Checked $python @((Join-Path $installRoot 'packaging\check_install.py'))

    if (-not $NoShortcut) {
        & (Join-Path $installRoot 'Install-Tray.ps1')
        $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Airplay2PC'
        New-Item -Path $key -Force | Out-Null
        New-ItemProperty -Path $key -Name DisplayName -Value 'Airplay2PC' -Force | Out-Null
        New-ItemProperty -Path $key -Name DisplayVersion -Value $manifest.version -Force | Out-Null
        New-ItemProperty -Path $key -Name Publisher -Value 'mrk1987' -Force | Out-Null
        New-ItemProperty -Path $key -Name InstallLocation -Value $installRoot -Force | Out-Null
        New-ItemProperty -Path $key -Name DisplayIcon -Value (Join-Path $installRoot 'assets\icons\Airplay2PC-logo.ico') -Force | Out-Null
        $uninstall = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $installRoot 'packaging\Uninstall.ps1') + '"'
        New-ItemProperty -Path $key -Name UninstallString -Value $uninstall -Force | Out-Null
        New-ItemProperty -Path $key -Name NoModify -Value 1 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $key -Name NoRepair -Value 1 -PropertyType DWord -Force | Out-Null
    }
    @{version=$manifest.version; root=$installRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $installRoot 'installation.json') -Encoding UTF8
    $checkedWork = [IO.Path]::GetFullPath($work)
    if ((Split-Path $checkedWork -Parent) -ne $installRoot -or (Split-Path $checkedWork -Leaf) -ne '.setup' -or
        ((Get-Item -LiteralPath $checkedWork).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Setup cleanup path validation failed.'
    }
    Remove-Item -LiteralPath $checkedWork -Recurse -Force
    Write-Host 'Installed. Choose your LAN interface in Settings, then Start.'
    Write-Host 'Allow Python on your private network if Windows asks about the firewall.'
    if (-not $NoLaunch) { & (Join-Path $installRoot 'Start-Tray.ps1') -Settings }
    exit 0
} catch {
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    if (Get-Variable installRoot -ErrorAction SilentlyContinue) {
        Write-Host "The partial installation was left at $installRoot. No receiver was started."
    }
    exit 1
}
