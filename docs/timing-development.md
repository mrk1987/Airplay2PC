# Experimental timing pipeline

As of 2026-11-02, the timing code is ready to test against captured data but
isn't connected to audio scheduling. Playback still uses the existing receiver.
It sounds in sync in my setup; I haven't measured the acoustic alignment.

## Implemented

The experimental pipeline uses `perf_counter_ns()` / QueryPerformanceCounter.
On this Python 3.12 Windows host, `monotonic_ns()` was verified to use
GetTickCount64 with 15.625 ms resolution; it must not be used or mixed into new
timing records. QPC reports 100 ns resolution. Capture files identify their clock;
replay refuses clock fitting on untagged or incompatible records.

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

## Evidence

41 offline tests pass, including synthetic 30-minute clock/drift scenarios, packet
reordering/duplication, sequence rollover, correction arithmetic, malformed frames,
clock steps/expiry, pause/reanchor behavior, diagnostic redaction and replay.
Simulation uses declared delay/rate bounds; it is not a real 30-minute listening test.
The initial two patches reproduced the three modified upstream files (allowing
CRLF/LF differences). The 0.1 release adds fixed-delay and discovery-cleanup patches.

Review found overflow, forward-step lifecycle and high-rate-window bugs.
They're fixed and covered by regression tests. See the research ledger.

A silent 20-second probe tonight captured no PTP packets: inconclusive, not a
regression of earlier active-group reachability. Read-only device enumeration showed
MME as the default host API with reported 90/180 ms low/high latency; WASAPI is available.
These latency values are metadata, not measured DAC or acoustic delay. No stream opened.

## Next tests

1. Launch with `-TimingDiagnostics` to preserve real anchors without changing playback.
2. Start grouped playback and capture/replay PTP as described in validation.md.
3. Verify source/master relationship, anchor semantics and receive jitter. In particular,
   measure the realtime RTP latency policy; do not transplant Shairport's 11025-frame adjustment.
4. Implement a worker-driven callback backend with actual output clock calibration
   and continuous resampling. Python fitting, allocation, file writes and locks stay
   outside the real-time callback. The current drift policy returns decisions only.
5. Gate opt-in synced output on valid clocks/anchors, then validate acoustically.

The source list and design trade-offs are in [research notes](timing-research/DESIGN.md).
