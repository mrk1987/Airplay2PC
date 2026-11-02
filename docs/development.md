# Development layout

| Path | Contents |
|---|---|
| `packaging/Start-Airplay.ps1` | Windows receiver launcher |
| `packaging/Start-Tray.ps1`, `packaging/Install-Tray.ps1` | Tray launcher and per-user Start menu shortcut |
| `packaging/Test-Airplay.ps1` | Offline regression runner |
| `packaging/requirements-windows.txt` | Verified Python dependency versions |
| `patches/` | Changes against the pinned upstream commit |
| `tests/` | Offline playback regressions |
| `tools/` | Maintained diagnostic commands |
| `tray_app/` | Native Windows tray UI and receiver process supervision |
| `timing/` | Experimental PTP, anchors, clock mapping and scheduling policy; not connected to audio output |
| `docs/` | Setup, implementation and validation guidance |

## Run from a checkout

Check for an existing **PC AirPlay** instance before starting another copy.
From PowerShell in this directory:

```powershell
.\packaging\Start-Airplay.ps1 -ListInterfaces
.\packaging\Start-Airplay.ps1 -NetInterface '{YOUR-LAN-INTERFACE-GUID}'
```

Choose the physical LAN interface. The launcher uses `.venv/`, preserves
`runtime/pairings/`, and enables redundant RTP payloads with `-ftor 61`. Ctrl+C stops
the foreground receiver. No startup service or firewall changes are installed.
