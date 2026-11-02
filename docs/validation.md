# Testing

As of 2026-11-02, playback is clean, iPhone volume control works, and sync
sounds spot on to my ear. I've listened with Spotify set to lossless streaming.
That doesn't establish an end-to-end lossless path or a measured sync tolerance.

## Release 0.1 checks

Version 0.1.1 adds tests for automatic startup, first-run interface selection,
development-shortcut migration and preservation of unrelated shortcuts.
All 70 tests pass. The installer and launch scripts use the grouped
`packaging/` layout.

The online installer completed in an empty directory with spaces in its path.
Its private Python 3.12.12 runtime loaded Tcl/Tk and all native dependencies.
The installed copy passed its 59 regression tests with zeroconf 0.149.16.
Four further setup and discovery tests bring the suite to 63 passing tests,
including corrupt payload rejection, protection of an occupied destination,
and discovery cleanup. A loopback mDNS check reproduced a shutdown hang with
the old asynchronous unregister call; the synchronous API completed normally.
The uninstaller
removed the isolated test installation and kept its `runtime/` data.
The compiled EXE extracted the expected four setup files and uses an
`asInvoker` manifest, so it doesn't request administrator access.

Secret scanning covered all nine pre-release commits and the installer payload.
No leaks were found. The dependency check assessed all 24 pinned release
packages and found no known advisories at those versions on 2026-11-02.
These checks don't replace a full upstream security audit or a fresh Windows VM test.

## Playback and timing

1. Exact nonzero ALAC PCM roundtrip and byte counts: zero differences. PASSED for
   16/24-bit, 352/1024 samples. Buffer/rate regressions also pass.
2. Native startup: registers mDNS and listens on LAN port 7000. PASSED.
3. Listening: I no longer hear robotic sound or rubber-banding. Sync also sounds
   right in my setup. A documented 30-minute run with no audible speed changes
   is still on the list.
4. Multiroom: select PC plus an existing room. Measure acoustic impulses from both
   outputs at matched microphone distance. Target absolute difference <=10 ms at
   start and <=10 ms change after 30 minutes. NOT MEASURED.
5. Only if gate 4 fails: verify active-group UDP319/320 exchange and clock identity,
   implement PTP offset/path-delay estimation, preserve full network/RTP anchors,
   schedule by actual DAC output time, then add controlled drift correction. Unit
   clock tests plus acoustic gate 4 must pass before claiming synced playback.

## Timing reachability — 2026-11-02

A 20-second passive probe received 142 Sync messages, 142 FollowUp messages,
71 Announce messages and 71 Signaling messages; all 142 Sync/FollowUp pairs
matched. This supersedes the earlier inconclusive eight-second idle probe.
It establishes PTP traffic reachability, not clock accuracy or acoustic alignment.

For another timing check, start grouped playback before running:

```powershell
.\.venv\Scripts\python.exe tools/probe_ptp.py --interface YOUR-LAN-IP --seconds 20
```

The probe receives timing packets and never adjusts the Windows clock. It is
not a synchronisation service. Do not infer audio alignment from its offsets.

I haven't done the acoustic measurements yet.

## Capture and replay timing without audio output

While an existing group is active, optionally save a private PTP-only trace:

```powershell
.\.venv\Scripts\python.exe tools/probe_ptp.py --interface YOUR-LAN-IP --seconds 120 --capture runtime/timing/group.jsonl
.\.venv\Scripts\python.exe tools/replay_timing.py runtime/timing/group.jsonl
```

Capture refuses to overwrite existing files. Keep traces local: PTP packets include
clock identities. The replay opens no sockets or audio hardware. No matched pairs
returns a nonzero exit status and must not be interpreted as successful validation.
Fitting additionally requires an explicit source-port identity, master ID and
`--assumed-max-delay-us`; that delay value is an assumption, not a measurement.

See [Timing development](timing-development.md) for the current implementation and
remaining backend, delay-measurement and acoustic gates.
