# Current design — 2026-11-02

Immediate goal: clean single-speaker playback. Andreas confirmed this after the
padding, format and packet-buffer fixes. Preserve this working baseline.
Ultimate goal: office PC speakers play in sync with existing AirPlay 2 rooms.

| Part | Choice | Rejected or deferred |
|---|---|---|
| Receiver | Existing Python receiver + tested patches | Replacing working pairing/decode before the playback test adds uncertainty. |
| Windows audio | Existing PyAudio sink, correctly sized s16 PCM | Whole AVFrame planes contain allocation padding. |
| Timing research | Virtual PTP clock + DAC-aware playback if group tests fail | System-clock modification is unnecessary and intrusive. |
| Reference implementation | goplay2 feature/audio-sync; Shairport Sync/NQPTP | goplay2 main has incomplete timing; README clock accuracy is not proof of audio accuracy. |
| WSL/Cygwin | Deferred | Prior notes report WSL2 firmware blocker. Shairport Cygwin docs explicitly exclude AirPlay 2. |
| Commercial software | Unverified | AirServer Connect hardware supports multiroom; that does not establish Windows Desktop support. |

## Test gates

1. Exact nonzero ALAC PCM roundtrip and byte counts: zero differences. PASSED for
   16/24-bit, 352/1024 samples. Buffer/rate regressions also pass.
2. Native startup: registers mDNS and listens on LAN port 7000. PASSED.
3. Audible playback: user reports no robotic sound or rubber-banding. PASSED for
   current listening session. Next durability gate: 30 minutes with zero audible speed changes.
4. Multiroom: select PC plus an existing room. Measure acoustic impulses from both
   outputs at matched microphone distance. Target absolute difference <=10 ms at
   start and <=10 ms change after 30 minutes. NOT MEASURED.
5. Only if gate 4 fails: verify active-group UDP319/320 exchange and clock identity,
   implement PTP offset/path-delay estimation, preserve full network/RTP anchors,
   schedule by actual DAC output time, then add controlled drift correction. Unit
   clock tests plus acoustic gate 4 must pass before claiming synced playback.

## Sources (primary)

- https://github.com/openairplay/airplay2-receiver — accurate audio sync explicitly missing.
- https://github.com/openairplay/goplay2 — Windows excluded; buffered AAC only.
- https://raw.githubusercontent.com/openairplay/goplay2/feature/audio-sync/audio/player.go
- https://raw.githubusercontent.com/openairplay/goplay2/feature/audio-sync/audio/clock.go
- https://github.com/mikebrady/shairport-sync/blob/master/CYGWIN.md — AirPlay 2 unsupported.
- https://github.com/mikebrady/nqptp — Linux/FreeBSD PTP timing companion.
- https://www.airserver.com/WindowsDesktop — Windows multiroom support not established.

Independent research agent found no verified drop-in native Windows alternative
among these candidates. Local Qwen reviewer identified network-coupled playback
as a possible jitter weakness, but also offered incorrect queue/pacing claims.
Those suggestions were not blindly applied: removing startup buffering would
trade jitter tolerance for lower latency, and subtracting monotonic time twice is
wrong. No new playback-loop rewrite after the successful listening test.
