"""Real shortcut migration in a temporary folder, without changing the Start menu."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows shortcut checks')
class ShortcutTests(unittest.TestCase):
    def invoke(self, script, *arguments):
        return subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(script), *map(str, arguments)], capture_output=True, text=True, timeout=30)

    def prepare(self, folder):
        root = Path(folder)
        app = root / 'new installation'
        for name in ('packaging', '.venv/Scripts', 'tray_app', 'assets/icons'):
            (app / name).mkdir(parents=True, exist_ok=True)
        (app / '.venv/Scripts/pythonw.exe').touch()
        (app / 'tray_app/app.py').touch()
        shutil.copyfile(ROOT / 'assets/icons/Airplay2PC-logo.ico', app / 'assets/icons/Airplay2PC-logo.ico')
        shutil.copyfile(ROOT / 'packaging/Install-Tray.ps1', app / 'packaging/Install-Tray.ps1')
        helper = root / 'shortcut.ps1'
        helper.write_text('''param([string]$Path,[string]$Target,[string]$App)
$ErrorActionPreference='Stop'
$env:PSModulePath=(Join-Path $PSHOME 'Modules')+[IO.Path]::PathSeparator+$env:PSModulePath
$link=(New-Object -ComObject WScript.Shell).CreateShortcut($Path)
if ($Target) { $link.TargetPath=$Target; $link.Arguments='"'+$App+'"'; $link.Save() }
@{target=$link.TargetPath;arguments=$link.Arguments;icon=$link.IconLocation}|ConvertTo-Json
''', encoding='utf-8')
        return root, app, helper

    def test_development_shortcut_migrates_and_gets_the_logo(self):
        with tempfile.TemporaryDirectory() as folder:
            root, app, helper = self.prepare(folder)
            old = root / 'old development'
            (old / '.venv/Scripts').mkdir(parents=True)
            (old / 'tray_app').mkdir()
            (old / '.venv/Scripts/pythonw.exe').touch()
            (old / 'tray_app/app.py').touch()
            link = root / 'Airplay2PC.lnk'
            made = self.invoke(helper, '-Path', link, '-Target', old / '.venv/Scripts/pythonw.exe', '-App', old / 'tray_app/app.py')
            self.assertEqual(made.returncode, 0, made.stderr)
            migrated = self.invoke(app / 'packaging/Install-Tray.ps1', '-ShortcutPath', link)
            self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
            result = self.invoke(helper, '-Path', link)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertTrue(os.path.samefile(value['target'], app / '.venv/Scripts/pythonw.exe'))
            self.assertTrue(value['arguments'].startswith('"') and value['arguments'].endswith('"'))
            self.assertTrue(os.path.samefile(value['arguments'][1:-1], app / 'tray_app/app.py'))
            icon_path, icon_index = value['icon'].rsplit(',', 1)
            self.assertEqual(icon_index, '0')
            self.assertTrue(os.path.samefile(icon_path, app / 'assets/icons/Airplay2PC-logo.ico'))

    def test_unrelated_shortcut_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root, app, helper = self.prepare(folder)
            link = root / 'unrelated.lnk'
            target = Path(os.environ['WINDIR']) / 'System32/notepad.exe'
            self.assertEqual(self.invoke(helper, '-Path', link, '-Target', target, '-App', 'unrelated.txt').returncode, 0)
            before = link.read_bytes()
            result = self.invoke(app / 'packaging/Install-Tray.ps1', '-ShortcutPath', link)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unrelated shortcut', result.stderr)
            self.assertEqual(link.read_bytes(), before)
