# Airplay2PC

Native Windows AirPlay 2 audio receiver workspace, with a small patch set for
openairplay/airplay2-receiver. **Clean playback confirmed by Andreas on
2026-11-02**, after fixing robotic sound and speed rubber-banding.
Cross-room synchronisation and long-run drift are still unverified.

## Run on this PC

The receiver advertises as **PC AirPlay**. Check for an existing instance before
starting another copy. Open PowerShell in this directory:

```powershell
.\Start-Airplay.ps1 -ListInterfaces
.\Start-Airplay.ps1 -NetInterface '{YOUR-LAN-INTERFACE-GUID}'
```

Choose the physical LAN interface, not a VPN adapter. The launcher uses the
existing Python environment, preserves this workspace's pairing store, and enables
redundant RTP payload support with `-ftor 61`. Ctrl+C stops the foreground receiver.
No startup service or firewall changes are installed.

## Reproduce the patched source

This private repository contains patches and tests, rather than a copy of the
unlicensed upstream source. The local upstream checkout remains separate and ignored.

```powershell
git clone https://github.com/openairplay/airplay2-receiver.git
git -C airplay2-receiver checkout 6c343d3679ddb561c61566985acaaf587d0a3bd3
git -C airplay2-receiver apply --check ../patches/windows-playback.patch
git -C airplay2-receiver apply ../patches/windows-playback.patch
uv venv --python 3.12 .venv-ap2
uv pip install --python .venv-ap2/Scripts/python.exe -r requirements-windows.txt
.\.venv-ap2\Scripts\python.exe -m unittest discover -s tests -v
```

The existing machine has the required dependencies. Fresh Windows installations
may need C/C++ build tools for netifaces; a fresh-machine install has not been tested.
The patch includes the previous local audio changes as well as this repair.
Do not apply it a second time to the current checkout.

## Playback repairs

See [Playback repairs](docs/PLAYBACK-FIXES.md) for the measured padding bug,
packet-buffer corrections, volume routing and regression coverage.

## Multiroom status

The receiver can advertise and accept AirPlay 2 streams, but upstream does not
implement accurate PTP/NTP sync. `SETRATEANCHORTIME` currently forwards only RTP
sample time; playback anchors to local message receipt rather than the shared
network clock. Clean playback does not prove room alignment.

See [Design and test gates](research/DESIGN.md) for verified alternatives and test gates.
`tools/ptp_probe.py` is a passive timing reachability tool, not a clock sync service.
A 20-second probe on 2026-11-02 received 142 matched Sync/FollowUp pairs.
This confirms timing traffic is reachable; clock accuracy and room alignment
remain unmeasured. Acoustic tests are deferred until daytime.

## Workspace layout

| Path | Purpose | Tracked |
|---|---|---|
| `Start-Airplay.ps1` | Receiver launcher | Yes |
| `requirements-windows.txt` | Verified dependency versions | Yes |
| `patches/` | Patch against the pinned upstream commit | Yes |
| `tests/` | Offline audio and buffer regressions | Yes |
| `tools/ptp_probe.py` | Passive timing reachability probe | Yes |
| `docs/` | Playback repair details | Yes |
| `research/` | Design, evidence ledger and research scope | Yes |
| `airplay2-receiver/` | Patched upstream checkout | No |
| `.venv-ap2/`, `analysis-venv/` | Local Python environments | No |
| `pairings/`, `airplay_capture/` | Private trust data and recordings | No |
| `scratchpad/` | Historical scripts, notes, logs and WSL image | No |
| Root `*.log` | Current receiver log paths | No |

The repository uses an explicit file allowlist in `.gitignore`. Add new source
files deliberately; keep credentials, device settings, recordings and backups
outside commits. Archived experiments are unsupported and may contain old paths.
Use this README for current operation.
