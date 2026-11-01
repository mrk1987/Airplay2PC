# Setup and development

This private repository contains patches and tests, rather than a copy of the
unlicensed upstream source. The local upstream checkout remains separate and ignored.

```powershell
New-Item -ItemType Directory -Force vendor | Out-Null
git clone https://github.com/openairplay/airplay2-receiver.git vendor/airplay2-receiver
git -C vendor/airplay2-receiver checkout 6c343d3679ddb561c61566985acaaf587d0a3bd3
git -C vendor/airplay2-receiver apply --check ../../patches/windows-playback.patch
git -C vendor/airplay2-receiver apply ../../patches/windows-playback.patch
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

The patch targets the pinned commit above. After an intentional upstream edit,
regenerate it with `git -C vendor/airplay2-receiver diff --binary` and save the output
as `patches/windows-playback.patch` without changing its encoding or line endings.
Review the patch for private data, run the offline tests, and verify it applies
to a clean checkout of the pinned commit before committing a replacement.

## Workspace migration on 2026-11-02

The upstream checkout moved into `vendor/`, pairing data and current logs into
`runtime/`, and captures into `archive/audio-captures/`. Pairing file hashes
were verified unchanged. The active `.venv/` was recreated from the pinned
requirements rather than moved. Old environments are retained under
`archive/environments/` for reference and should not be activated.
