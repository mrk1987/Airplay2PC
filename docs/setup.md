# Setup and development

For normal use, download the installer from [Releases](https://github.com/mrk1987/Airplay2PC/releases).
It downloads Python and the receiver, installs the dependencies and creates a
Start menu shortcut. See [Building a release](release.md) for packaging details.

For development, use the commands below. You'll need Git and uv installed.
I keep the upstream receiver in a separate, ignored checkout because its
pinned revision has no licence file.

```powershell
New-Item -ItemType Directory -Force vendor | Out-Null
git clone https://github.com/openairplay/airplay2-receiver.git vendor/airplay2-receiver
git -C vendor/airplay2-receiver checkout 6c343d3679ddb561c61566985acaaf587d0a3bd3
git -C vendor/airplay2-receiver apply --check ../../patches/windows-playback.patch
git -C vendor/airplay2-receiver apply ../../patches/windows-playback.patch
git -C vendor/airplay2-receiver apply --check ../../patches/timing-diagnostics.patch
git -C vendor/airplay2-receiver apply ../../patches/timing-diagnostics.patch
git -C vendor/airplay2-receiver apply --check ../../patches/output-delay.patch
git -C vendor/airplay2-receiver apply ../../patches/output-delay.patch
git -C vendor/airplay2-receiver apply --check ../../patches/network-discovery.patch
git -C vendor/airplay2-receiver apply ../../patches/network-discovery.patch
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-windows.txt
```

The manual setup may need C/C++ build tools for netifaces. The release installer
includes a Windows wheel for it. Apply the patches once, in the order shown.

## Offline checks

Run from the project root. These tests do not open audio hardware or use the network:

```powershell
.\Test-Airplay.ps1
```

The launcher and tests resolve `vendor/airplay2-receiver/` and `.venv/` from the
project root. The test runner puts generated logs in `runtime/test-logs/`.
The receiver launcher uses `runtime/` as its working directory, preserving
pairings under `runtime/pairings/`. Use the launcher to retain pairing trust.

## Updating the patch

All four patches target the pinned commit above, applied in the order shown.
`windows-playback.patch` contains the playback fixes. The second patch
adds optional anchor logging only; it is inactive unless the launcher enables it.
`output-delay.patch` adds the optional fixed PCM delay and is inactive at the
default 0 ms. Do not apply any patch twice to the existing checkout.

`network-discovery.patch` uses zeroconf's synchronous unregister API so shutdown
completes on the library's event loop. The release uses zeroconf 0.149.16.

When regenerating patches, first reverse `network-discovery.patch`, then
`output-delay.patch`, then reverse
`timing-diagnostics.patch` before exporting
the playback diff with `git -C vendor/airplay2-receiver diff --binary`. Then reapply
the diagnostic changes and export only that incremental diff as the second patch.
Do not fold both into the playback patch and then apply diagnostics a second time.
Review the patch for private data, run the offline tests, and verify it applies
to a clean checkout of the pinned commit before committing a replacement.

## Optional timing diagnostics

Add `-TimingDiagnostics` to the normal launcher command to record numeric anchors
under ignored `runtime/timing/anchors-<pid>.jsonl`. This does not enable synced
playback or record media, keys or complete protocol payloads. Files stop growing
at roughly 5 MB per process. The launcher restores its environment variables on exit.

## Local workspace

The upstream checkout lives in `vendor/`, pairing data and logs in `runtime/`,
and old captures in `archive/audio-captures/`. When I reorganised the workspace,
I checked that the pairing file hashes hadn't changed and recreated `.venv/`
from the pinned requirements. Old environments stay in `archive/environments/`
for reference; don't activate them.
