# Airplay2PC

Native Windows AirPlay 2 audio receiver workspace, with a small patch set for
openairplay/airplay2-receiver. **Clean playback confirmed by Andreas on
2026-11-02**, after fixing robotic sound and speed rubber-banding.
Cross-room synchronisation and long-run drift are still unverified.

## Run on this PC

The receiver is currently running as **PC AirPlay**. Do not start a second copy.
For a later restart, open PowerShell in this directory:

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

## What was repaired

- Strip PyAV alignment padding before audio output. A 352-sample stereo s16 frame
  has 1,408 valid bytes, but its resampled plane allocates 1,536 bytes. Playing
  all 1,536 adds 32 unwanted samples per channel every packet: 9.09% excess time
  plus arbitrary padding noise. Earlier buffered logs also show 4,224 bytes where
  4,096 are valid. This is a measured bug, not a codec-bit-depth guess.
- Preserve every decoded/resampled frame, including zero or multiple resampler outputs.
- Stop reading `48000` as `8000` when parsing the negotiated format.
- Keep packet, sequence and timestamp queues consistent when removing a packet.
  Sequence zero now works at rollover; flush preserves order and handles empty queues.
- Skip stale resends and choose the nearest future sequence after a gap.
- Configure 24-bit decode with PyAV's s32 container, match mono/stereo output,
  and use the negotiated ALAC samples per frame.
- Correct the legacy AES-key/IV selection condition.
- Route iPhone volume commands to the Windows playback process rather than the
  network-control process; the latter owns no audio session. Andreas confirmed the slider now controls PC volume.
- Remove unconditional plaintext and WAV recording from playback. Existing recordings stay local.

Seven regression tests pass, including nonzero stereo ALAC roundtrips for 16/24-bit
and 352/1024 samples, exact output size/channel order, rate selection across all
enumerated formats, sequence rollover, out-of-order packets, and empty flush.
Native startup and mDNS registration succeeded; Andreas confirmed clean sound.
This does not prove every fix contributed to that improvement.

## Multiroom status

The receiver can advertise and accept AirPlay 2 streams, but upstream does not
implement accurate PTP/NTP sync. `SETRATEANCHORTIME` currently forwards only RTP
sample time; playback anchors to local message receipt rather than the shared
network clock. Clean playback does not prove room alignment.

See [research/design.md](research/DESIGN.md) for verified alternatives and test gates.
`tools/ptp_probe.py` is a passive timing reachability tool, not a clock sync service.
An eight-second idle probe saw no PTP traffic; that is inconclusive without an active group.

## Local-only material

Pairings, recordings, logs, virtual environments, the old WSL image and exploratory
scripts are ignored. No pairing keys, device-specific network settings or recorded
audio are committed. `PROGRESS-2026-11-02.md` is historical and contains superseded
paths and status. Keep it as evidence; use this README for current operation.
