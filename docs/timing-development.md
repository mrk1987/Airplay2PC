# Experimental timing pipeline

As of 2026-11-02, the timing code is ready to test against captured data but
isn't connected to audio scheduling. Playback still uses the existing receiver.
It sounds in sync in my setup; I haven't measured the acoustic alignment.

## Implemented

The experimental pipeline uses `perf_counter_ns()` / QueryPerformanceCounter.
Capture files identify their clock, and replay rejects incompatible clock domains.
Do not mix these records with `monotonic_ns()` timestamps.

| Module | Responsibility |
|---|---|
| `timing/ptp.py` | PTPv2 header/timestamp validation; bounded Sync/FollowUp pairing; signed correction fields; overflow-sentinel rejection; source/domain/transport isolation |
| `timing/follower.py` | Selected-source clock fit, warm-up, rate bounds, conservative full-horizon uncertainty, expiry and discontinuity generations |
| `timing/anchors.py` | Buffered 64-bit fraction conversion; realtime records retain both RTP counters and require explicit latency policy |
| `timing/timeline.py` | Exact clock/RTP conversions, bounded validity and latency-aware deadlines |
| `timing/scheduler.py` | Offline scheduling state and bounded, slewed drift-control decisions |
| `timing/output_clock.py` | Bracketed PortAudio stream-clock to local-monotonic conversion; restart/expiry checks |
| `timing/diagnostics.py` | Optional private numeric anchor logging, capped per process, disabled by default |

A packet observation is **not a calibrated master clock**. The follower requires an
explicit assumed receive-delay ceiling. Its uncertainty includes that ceiling,
fit residual and full-horizon rate-error allowance. It does not measure path delay,
elect a master, implement peer awakening or prove Windows receive timestamp quality.
Reacquisition resets the generation so old anchors cannot be reused silently.

## Tests

The tests cover synthetic clock drift, packet reordering and duplication,
sequence rollover, correction arithmetic, malformed frames, clock steps,
expiry, pause/reanchor behaviour, diagnostic redaction and replay.
Synthetic scenarios use declared delay and rate bounds; they don't establish
real acoustic alignment or DAC timing accuracy.

## Next tests

1. Launch with `-TimingDiagnostics` to preserve real anchors without changing playback.
2. Start grouped playback and capture/replay PTP as described in validation.md.
3. Verify source/master relationship, anchor semantics and receive jitter. In particular,
   measure the realtime RTP latency policy; do not transplant Shairport's 11025-frame adjustment.
4. Implement a worker-driven callback backend with actual output clock calibration
   and continuous resampling. Python fitting, allocation, file writes and locks stay
   outside the real-time callback. The current drift policy returns decisions only.
5. Gate opt-in synced output on valid clocks/anchors, then validate acoustically.

## References

- [Shairport Sync RTP handling](https://github.com/mikebrady/shairport-sync/blob/master/rtp.c)
- [Shairport Sync RTSP handling](https://github.com/mikebrady/shairport-sync/blob/master/rtsp.c)
- [NQPTP message handling](https://github.com/mikebrady/nqptp/blob/main/nqptp-message-handlers.c)
- [PortAudio callback timing](https://portaudio.com/docs/v19-doxydocs/structPaStreamCallbackTimeInfo.html)
