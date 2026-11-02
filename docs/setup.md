# Setup and development

This private repository contains patches and tests, rather than a copy of the
unlicensed upstream source. The local upstream checkout remains separate and ignored.

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
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-windows.txt
```

The existing machine has the required dependencies. Fresh Windows installations
may need C/C++ build tools for netifaces; a fresh-machine install has not been tested.
The patch contains the complete local audio repair set.
Do not apply it a second time to the current checkout.

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

All three patches target the pinned commit above, applied in the order shown.
`windows-playback.patch` contains the accepted playback fixes. The second patch
adds optional anchor logging only; it is inactive unless the launcher enables it.
`output-delay.patch` adds the optional fixed PCM delay and is inactive at the
default 0 ms. Do not apply any patch twice to the existing checkout.

When regenerating patches, first reverse `output-delay.patch`, then reverse
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

## Workspace migration on 2026-11-02

The upstream checkout moved into `vendor/`, pairing data and current logs into
`runtime/`, and captures into `archive/audio-captures/`. Pairing file hashes
were verified unchanged. The active `.venv/` was recreated from the pinned
requirements rather than moved. Old environments are retained under
`archive/environments/` for reference and should not be activated.
