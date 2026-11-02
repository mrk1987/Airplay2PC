"""Build an allowlisted source ZIP and Windows online installer with IExpress."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from windows_icon import replace_icon

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    tracked = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}',
                                       '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0')
    roots = {'README.md', 'LICENSE', 'THIRD_PARTY.md', 'CHANGELOG.md', 'SECURITY.md',
             'VERSION', 'requirements-tray.txt', 'requirements-windows.txt', 'requirements-release.txt',
             'Install-Tray.ps1', 'Start-Tray.ps1', 'Start-Airplay.ps1', 'Test-Airplay.ps1',
             '.gitignore', '.gitattributes'}
    folders = {'assets', 'docs', 'packaging', 'patches', 'tests', 'timing', 'tools', 'tray_app', '.github'}
    result = []
    for name in filter(None, tracked):
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe source path')
        if name not in roots and path.parts[0] not in folders:
            raise ValueError(f'Unreviewed release path: {name}')
        if path.suffix in {'.pem', '.p12', '.pyc', '.log'} or path.name.startswith('.env'):
            raise ValueError(f'Private/generated release path: {name}')
        source = ROOT / path
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Release input is not a regular file: {name}')
        result.append(name)
    for name in roots:
        if name not in result:
            raise ValueError(f'Required release input is not tracked: {name}')
    return sorted(result)


def write_zip(destination, entries):
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for source, name in entries:
            info = zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, Path(source).read_bytes())


def build(wheel, output, compile_installer=True):
    version = (ROOT / 'VERSION').read_text().strip()
    if version != '0.1.0':
        raise ValueError('Review the release metadata before changing version')
    wheel = Path(wheel).resolve()
    if wheel.name != 'netifaces-0.11.0-cp312-cp312-win_amd64.whl':
        raise ValueError('Expected the netifaces 0.11.0 CPython 3.12 x64 wheel')
    with zipfile.ZipFile(wheel) as archive:
        licence_names = [n for n in archive.namelist() if n.endswith('/LICENSE') or n.endswith('/licenses/LICENSE')]
        if len(licence_names) != 1:
            raise ValueError('The netifaces wheel must include its licence')
        licence = archive.read(licence_names[0])
        if b'Alastair Houghton' not in licence or b'Permission is hereby granted' not in licence:
            raise ValueError('Unexpected netifaces licence')
    lock = (ROOT / 'requirements-release.txt').read_text()
    if digest(wheel) not in lock:
        raise ValueError('The wheel hash must appear in requirements-release.txt')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = output / 'installer-input'
    if package.exists():
        raise ValueError('Choose a new output directory; installer input already exists')
    package.mkdir()
    files = sources()
    entries = [(ROOT / name, name) for name in files]
    source_zip = output / f'Airplay2PC-{version}-source.zip'
    write_zip(source_zip, entries)
    licence_file = package / 'netifaces-LICENSE.txt'
    licence_file.write_bytes(licence)
    payload = package / 'payload.zip'
    write_zip(payload, entries + [(wheel, 'wheels/' + wheel.name),
                                 (licence_file, 'wheels/netifaces-LICENSE.txt')])
    for name in ('Setup.cmd', 'Setup.ps1'):
        (package / name).write_bytes((ROOT / 'packaging' / name).read_bytes())
    manifest = {'version': version, 'payload_sha256': digest(payload)}
    (package / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    exe = output / f'Airplay2PC-{version}-Setup.exe'
    names = ('Setup.cmd', 'Setup.ps1', 'payload.zip', 'manifest.json')
    sed = package / 'setup.sed'
    sed.write_text('\n'.join([
        '[Version]', 'Class=IEXPRESS', 'SEDVersion=3', '[Options]',
        'PackagePurpose=InstallApp', 'ShowInstallProgramWindow=1', 'HideExtractAnimation=0',
        'UseLongFileName=1', 'InsideCompressed=0', 'CAB_FixedSize=0', 'CAB_ResvCodeSigning=0',
        'RebootMode=N', 'InstallPrompt=Install Airplay2PC 0.1.0? An internet connection is required.',
        'DisplayLicense=', 'FinishMessage=', f'TargetName={exe}',
        'FriendlyName=Airplay2PC 0.1.0', 'AppLaunched=cmd.exe /c Setup.cmd',
        'PostInstallCmd=<None>', 'AdminQuietInstCmd=', 'UserQuietInstCmd=',
        'SourceFiles=SourceFiles', '[SourceFiles]', f'SourceFiles0={package}\\',
        '[SourceFiles0]', *[f'%FILE{i}%=' for i in range(len(names))],
        '[Strings]', *[f'FILE{i}="{name}"' for i, name in enumerate(names)], ''
    ]), encoding='ascii')
    if compile_installer:
        subprocess.run(['iexpress.exe', '/N', '/Q', str(sed)], check=True, timeout=180)
        if not exe.is_file() or exe.stat().st_size < payload.stat().st_size:
            raise ValueError('IExpress did not produce a complete installer')
        replace_icon(exe, ROOT / 'assets/icons/Airplay2PC-logo.ico')
    artifacts = [source_zip] + ([exe] if compile_installer else [])
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in artifacts), encoding='ascii')
    for artifact in artifacts:
        print(f'{artifact.name}: {artifact.stat().st_size:,} bytes')
    return package


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--netifaces-wheel', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--no-installer', action='store_true')
    args = parser.parse_args()
    build(args.netifaces_wheel, args.output, not args.no_installer)
