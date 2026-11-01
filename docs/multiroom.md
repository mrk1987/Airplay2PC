# Multiroom design

Goal: receive iPhone audio on native Windows PC speakers alongside existing
AirPlay 2 rooms, with stable playback and measured synchronisation. Preserve
the accepted clean playback and remote volume baseline.

## Current limitation

The receiver advertises and accepts AirPlay 2 streams, but does not implement
accurate shared-clock playback. `SETRATEANCHORTIME` forwards only RTP sample
time; playback anchors to local message receipt rather than the network clock.
Clean sound and reachable PTP traffic do not establish room alignment.

Measure acoustic alignment and long-run drift before changing the timing code.
See [Validation](validation.md) for acceptance targets and test commands.

## Implementation choices

| Part | Choice | Rejected or deferred |
|---|---|---|
| Receiver | Existing Python receiver + tested patches | Replacing working pairing/decode before the playback test adds uncertainty. |
| Windows audio | Existing PyAudio sink, correctly sized s16 PCM | Whole AVFrame planes contain allocation padding. |
| Timing research | Virtual PTP clock + DAC-aware playback if group tests fail | System-clock modification is unnecessary and intrusive. |
| Reference implementation | goplay2 feature/audio-sync; Shairport Sync/NQPTP | goplay2 main has incomplete timing; README clock accuracy is not proof of audio accuracy. |
| WSL/Cygwin | Deferred | Prior notes report WSL2 firmware blocker. Shairport Cygwin docs explicitly exclude AirPlay 2. |
| Commercial software | Unverified | AirServer Connect hardware supports multiroom; that does not establish Windows Desktop support. |

## If acoustic validation fails

Preserve full network/RTP anchors, estimate clock offset and path delay with a
virtual PTP clock, and schedule against actual DAC output time. Add controlled
drift correction only with clock tests and acoustic measurements. Changing
the Windows system clock is unnecessary.

Do not remove startup buffering or rewrite pacing based on speculative review
comments. Those changes have not been shown to improve the accepted baseline.

## Alternatives examined on 2026-11-02

No drop-in native Windows alternative was verified during the investigation.
The comparisons below are historical findings, not newly checked support claims.

- https://github.com/openairplay/airplay2-receiver — accurate audio sync explicitly missing.
- https://github.com/openairplay/goplay2 — Windows excluded; buffered AAC only.
- https://raw.githubusercontent.com/openairplay/goplay2/feature/audio-sync/audio/player.go
- https://raw.githubusercontent.com/openairplay/goplay2/feature/audio-sync/audio/clock.go
- https://github.com/mikebrady/shairport-sync/blob/master/CYGWIN.md — AirPlay 2 unsupported.
- https://github.com/mikebrady/nqptp — Linux/FreeBSD PTP timing companion.
- https://www.airserver.com/WindowsDesktop — Windows multiroom support not established.


## Scope

Native Windows is preferred. Earlier local investigation reported firmware
virtualisation disabled, so WSL2 was not a working route. No purchases or
machine-wide installation are part of the current implementation. Pairing
trust and private recordings must remain local.
