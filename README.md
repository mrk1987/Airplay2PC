# Airplay2PC

Native Windows AirPlay 2 audio receiver based on a pinned
`openairplay/airplay2-receiver` checkout and a maintained local patch.
Andreas confirmed clean playback and iPhone volume control on 2026-11-02.
Multiroom alignment and long-run drift remain unmeasured.

## Run

Check for an existing **PC AirPlay** instance before starting another copy.
From PowerShell in this directory:

```powershell
.\Start-Airplay.ps1 -ListInterfaces
.\Start-Airplay.ps1 -NetInterface '{YOUR-LAN-INTERFACE-GUID}'
```

Choose the physical LAN interface. The launcher uses `.venv-ap2/`, preserves
`pairings/`, and enables redundant RTP payloads with `-ftor 61`. Ctrl+C stops
the foreground receiver. No startup service or firewall changes are installed.

## Documentation

- [Setup and development](docs/setup.md): dependencies, pinned upstream, patch and offline checks.
- [Playback repairs](docs/playback-fixes.md): measured bugs and fixes.
- [Multiroom design](docs/multiroom.md): timing limitations, choices and alternatives.
- [Validation](docs/validation.md): verified results, remaining tests and timing probe usage.

## Repository layout

| Path | Contents |
|---|---|
| `Start-Airplay.ps1` | Windows receiver launcher |
| `requirements-windows.txt` | Verified Python dependency versions |
| `patches/` | Changes against the pinned upstream commit |
| `tests/` | Offline playback regressions |
| `tools/` | Maintained diagnostic commands |
| `docs/` | Setup, implementation and validation guidance |

## Local workspace

These paths are ignored and retain private data or machine-local dependencies:

| Path | Contents |
|---|---|
| `airplay2-receiver/` | Patched upstream source; kept separate because upstream has no licence |
| `.venv-ap2/` | Receiver Python environment |
| `analysis-venv/` | Existing analysis environment |
| `pairings/` | Private pairing trust |
| `airplay_capture/` | Private historical audio captures |
| `archive/` | Old experiments, logs, notes and installers, grouped by subject |
| Root `*.log` | Current receiver log paths |

Runtime paths stay in place because the receiver, launcher, environments and
historical tools depend on them. New experiments belong in `archive/`; reusable
diagnostics belong in `tools/`. Only deliberately reviewed files are allowed
through `.gitignore`. Keep credentials, recordings and device settings local.
