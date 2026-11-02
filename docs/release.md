# Building a release

The 0.1 installer is a Windows x64 online setup package, built with Windows'
built-in IExpress tool. It installs under `%LOCALAPPDATA%\Programs\Airplay2PC`.
It downloads a private Python 3.12 runtime, hash-locked packages and the pinned
upstream receiver. Python and Git don't need to be installed beforehand.

The receiver is fetched at setup time because its upstream revision has no
licence file. It isn't bundled in the EXE. See [Third-party notes](../THIRD_PARTY.md).

The installer is unsigned. Windows may show an unknown-publisher warning.
Check the download against `SHA256SUMS.txt` before running it.

## Build on Windows x64

Use Python 3.12 and a C compiler to build netifaces, then build the package:

```powershell
python -m pip wheel --no-deps netifaces==0.11.0 --wheel-dir wheelhouse
python packaging/build_release.py --netifaces-wheel wheelhouse/netifaces-0.11.0-cp312-cp312-win_amd64.whl --output dist/0.1.0
```

The wheel's SHA-256 must appear in `requirements-release.txt`. If you rebuilt
the wheel, add its hash to the netifaces entry after checking its contents and
licence. The build refuses an unrecognised wheel. Windows wheel builds can
have different hashes because compiler output isn't reproducible yet.

New files must be staged in Git before building. The builder only packages
tracked files from its explicit source allowlist. It never copies `runtime/`,
`.venv/`, `vendor/`, `archive/` or Git history.

The output contains the installer EXE, source ZIP, checksums and an
`installer-input/` directory for testing. Publish only the EXE, source ZIP and
checksums.

## Check before publishing

Run `Test-Airplay.ps1`. Check the PowerShell scripts parse without errors.
Install into an empty directory with a space in its name, using
`installer-input/Setup.ps1 -InstallDirectory PATH -NoShortcut -NoLaunch`.
This downloads dependencies without starting the receiver or modifying the
Start menu. Run the installed copy's tests too.

Also check the EXE extracts the expected four files, that a corrupt payload
fails before installing, and that an occupied destination is rejected.
A fresh Windows VM is still the best test of the complete click-through,
firewall prompt and uninstall flow.

## Uninstall

Quit the tray and stop the receiver, then use Windows' installed-apps list.
The uninstaller asks before removal and keeps `runtime/`, including pairing
trust, settings and logs. A new install can reuse that directory.

If setup fails, it leaves the partial directory in place for inspection and
doesn't start the receiver. Remove that partial installation before retrying.
