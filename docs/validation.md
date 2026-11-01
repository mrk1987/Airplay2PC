# Validation status

1. Exact nonzero ALAC PCM roundtrip and byte counts: zero differences. PASSED for
   16/24-bit, 352/1024 samples. Buffer/rate regressions also pass.
2. Native startup: registers mDNS and listens on LAN port 7000. PASSED.
3. Audible playback: user reports no robotic sound or rubber-banding. PASSED for
   the accepted listening session on 2026-11-02. Next durability gate: 30 minutes with zero audible speed changes.
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

When daytime testing resumes, start grouped playback before running:

```powershell
.\.venv\Scripts\python.exe tools/probe_ptp.py --interface YOUR-LAN-IP --seconds 20
```

The probe receives timing packets and never adjusts the Windows clock. It is
not a synchronisation service. Do not infer audio alignment from its offsets.

Acoustic testing is deferred until daytime at Andreas' request.

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
