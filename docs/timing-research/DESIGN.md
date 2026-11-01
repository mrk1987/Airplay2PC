# Experimental timing design

| Part | Choice | Rejected alternative and reason |
|---|---|---|
| PTP wire handling | Independent bounded parser/matcher; preserve signed correction precision (H4) | Blindly copy NQPTP's receive-biased offset (H1) |
| Clock mapping | Explicit selected source; exact fit; assumed receive-delay ceiling; expiry/generation (H5) | Treat timing reachability as calibrated clock accuracy |
| Buffered anchors | 64-bit binary fraction and explicit master identity (H2) | NTP 32-bit conversion: wrong unit scale |
| Realtime anchors | Keep both counters; require measured adjustment (H3) | Copy 11025-frame policy to every format |
| Output clock | Worker calibration of PortAudio stream time; callback DAC timestamp (H6) | Infer actual DAC time from blocking write duration |
| Drift correction | Bounded/slewed offline controller; future continuous resampler | Drop/repeat PCM blocks or vary sleep to correct clock drift |
| Integration | Optional numeric diagnostics first (H8) | Replace accepted playback before real observations |

## Gates in order

1. Offline regressions: 41/41 pass, no network/audio device required.
2. Reproducibility: both patches apply in order to pinned upstream; all three edited files match ignoring line-ending translation.
3. Captured-data pilot: at least 120 seconds of active-group PTP and anchor data; zero source/domain cross-matches; every usable buffered anchor preserves its uint64 clock ID and fraction. Report invalid/unmatched counts explicitly.
4. Host calibration: establish actual receive-delay/stream-clock error budgets. Mapping uncertainty must fit a 5 ms diagnostic budget across its full horizon; assumed bounds do not count as measurements.
5. Experimental backend: callback timestamp discontinuities, stale anchors and starvation fail closed; 30-minute instrumented output run with zero underruns and no uncontrolled sample drops/repeats. Audio backend/resampler not implemented yet.
6. Acoustic acceptance: <=10 ms initial PC/reference separation and <=10 ms change over 30 minutes, plus pause/seek/group rejoin recovery. Deferred until daytime.

## Open risks

- No master election/peer-awakening service or authenticated peer configuration yet.
- Unknown actual Windows timestamp jitter and path asymmetry.
- Realtime anchor latency policy and sender field variants require captured evidence.
- Output-clock metadata and successful synthetic control do not prove DAC timestamp accuracy.
- Callback backend and continuous resampler remain implementation work after the captured-data gate.
