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
| Commercial software | Unverified | AirServer Connect hardware supports multiroom; that does not establish Windows Desktop support. |

## If acoustic validation fails

Preserve full network/RTP anchors, estimate clock offset and path delay with a
virtual PTP clock, and schedule against actual DAC output time. Add controlled
drift correction only with clock tests and acoustic measurements. Changing
the Windows system clock is unnecessary.

I'm keeping the working buffering and pacing unless a listening test or
measurement shows a problem worth fixing.
