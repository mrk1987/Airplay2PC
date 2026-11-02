"""Installer patch integrity checks; no network or audio hardware."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'packaging/apply_patches.py'
spec = importlib.util.spec_from_file_location('release_patches', MODULE)
patches = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patches)


class PatchTests(unittest.TestCase):
    def run_patch(self, content, patch):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'example.py'
            target.write_text(content, encoding='utf-8')
            delta = root / 'change.patch'
            delta.write_text(patch, encoding='utf-8')
            patches.apply_patch(root, delta)
            return target.read_text(encoding='utf-8')

    def test_multiple_hunks_preserve_unchanged_lines(self):
        result = self.run_patch('a\nb\nc\nd\ne\n',
            '--- a/example.py\n+++ b/example.py\n@@ -1,2 +1,3 @@\n a\n-b\n+B\n+extra\n'
            '@@ -4,2 +5,2 @@\n d\n-e\n+E\n')
        self.assertEqual(result, 'a\nB\nextra\nc\nd\nE\n')

    def test_bad_context_leaves_source_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'example.py'
            target.write_text('original\n', encoding='utf-8')
            delta = root / 'bad.patch'
            delta.write_text('--- a/example.py\n+++ b/example.py\n@@ -1 +1 @@\n-wrong\n+replacement\n')
            with self.assertRaisesRegex(ValueError, 'context mismatch'):
                patches.apply_patch(root, delta)
            self.assertEqual(target.read_text(), 'original\n')

    def test_parent_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe patch path'):
            self.run_patch('a\n', '--- a/../outside.py\n+++ b/../outside.py\n@@ -1 +1 @@\n-a\n+b\n')

    def test_incorrect_counts_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'line counts'):
            self.run_patch('a\n', '--- a/example.py\n+++ b/example.py\n@@ -1,2 +1 @@\n-a\n+b\n')


@unittest.skipUnless(os.name == 'nt', 'Windows setup checks')
class SetupTests(unittest.TestCase):
    def setup(self, script, destination):
        return subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(script), '-InstallDirectory', str(destination), '-NoShortcut', '-NoLaunch'],
            capture_output=True, text=True, timeout=20)

    def test_occupied_destination_is_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'existing.txt'
            marker.write_text('keep me')
            result = self.setup(MODULE.with_name('Setup.ps1'), root)
            self.assertEqual(result.returncode, 1)
            self.assertIn('destination is not empty', result.stdout)
            self.assertEqual(marker.read_text(), 'keep me')
            self.assertEqual(list(root.iterdir()), [marker])

    def test_corrupt_payload_is_rejected_before_downloads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = root / 'Setup.ps1'
            script.write_bytes(MODULE.with_name('Setup.ps1').read_bytes())
            (root / 'manifest.json').write_text(json.dumps({'payload_sha256': '0' * 64}))
            (root / 'payload.zip').write_bytes(b'corrupt')
            destination = root / 'installation'
            result = self.setup(script, destination)
            self.assertEqual(result.returncode, 1)
            self.assertIn('payload checksum mismatch', result.stdout)
            self.assertNotIn('Downloading', result.stdout)
            self.assertFalse((destination / '.venv').exists())
            self.assertFalse((destination / 'installation.json').exists())
