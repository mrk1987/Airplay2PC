# Multiroom design

I want my Windows PC speakers to play alongside my other AirPlay 2 speakers.
It now sounds in sync to me, with clean playback and working iPhone volume
control. I haven't measured the acoustic offset or long-run drift.

## Current limitation

The receiver advertises and accepts AirPlay 2 streams, but does not implement
accurate shared-clock playback. `SETRATEANCHORTIME` forwards only RTP sample
time; playback anchors to local message receipt rather than the network clock.
My listening test is encouraging, but it doesn't establish clock accuracy.

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

I'm keeping the working buffering and pacing unless a listening test or
measurement shows a problem worth fixing.

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

I'm keeping this native to Windows. WSL2 wasn't a working option on the test
machine because firmware virtualisation was disabled. The current setup needs
no purchases or machine-wide installation. Pairings and recordings stay local.
