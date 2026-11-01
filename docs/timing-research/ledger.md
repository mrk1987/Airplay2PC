# Timing evidence ledger â€” 2026-11-02

| ID | Claim | Verdict | Evidence |
|---|---|---|---|
| H1 | Raw packet arrival yields unbiased master time | Invalidated | Primary NQPTP handler uses a receive-biased offset; no measured one-way delay |
| H2 | SETRATEANCHORTIME fraction is 32-bit NTP fraction | Invalidated | Primary Shairport rtsp.c uses networkTimeFrac uint64; parser tests use 2^63 = half a second |
| H3 | Realtime RTP counter maps directly without latency policy | Insufficient evidence | Primary Shairport rtp.c applies a 11025-frame adjustment; both counters now preserved |
| H4 | Packet matching/corrections can be verified offline | Validated within tests | Parser and replay tests cover signed fractional corrections, overflow sentinel, ordering, domain/source isolation and sequence zero |
| H5 | Clock fit/controller can handle bounded drift and delay | Partial | 30-minute synthetic scenarios pass under explicit assumed bounds; real Windows delay unmeasured |
| H6 | Default Windows API is WASAPI | Invalidated on this host | Live read-only PyAudio query: default MME; WASAPI available; no stream opened |
| H7 | Tonight's passive capture can validate clock fit | Inconclusive | 20-second silent probe yielded zero packets; no sender activity requested |
| H9 | Python 3.12 Windows monotonic_ns is high resolution | Invalidated on this host | Live get_clock_info: GetTickCount64 15.625 ms; perf_counter uses QPC 100 ns. New pipeline uses QPC and explicit clock metadata |
| H8 | Diagnostic logging can be isolated from audio/privacy | Validated within tests | Disabled by default; numeric field allowlist, IO containment and cap tests; no keys/media recorded |

## Rounds

1. Primary-code research plus independent Codex/Claude inspection corrected fraction width, RTP latency assumptions and path-delay claims.
2. Implemented packet/anchor/follower modules and synthetic replay. Claude found reserved correction sentinel, forward steps, high-rate window and weak sequence test; verified and fixed. Local Qwen supplied malformed-packet cases; several were already tested and were not counted as new findings.
3. Added bounded scheduler/drift decisions, PortAudio clock bridge and opt-in numeric anchor diagnostics. Silent probe was inconclusive; no audio stream opened. Added replay, redaction, IO-failure and output-clock tests.
4. Final independent attack identified the Windows clock-resolution blocker. Verified it live and switched experimental timestamps to QPC with clock-domain guards. Independent review also found malformed JSONL input shapes; fixed and tested. All prior lifecycle/correction findings confirmed addressed. Reproducibility checks passed ignoring LF/CRLF translation. Remaining hardware/sender uncertainties stay explicit; code defects found by the verifier are addressed before commit. No acoustic acceptance implied.

## Primary sources

- https://github.com/mikebrady/nqptp/blob/main/nqptp-message-handlers.c
- https://github.com/mikebrady/shairport-sync/blob/master/rtsp.c (SETRATEANCHORTIME)
- https://github.com/mikebrady/shairport-sync/blob/master/rtp.c (realtime 0xd7)
- https://standards.ieee.org/wp-content/uploads/import/documents/interpretations/1588-2008_interp.pdf (correction overflow sentinel)
- https://portaudio.com/docs/v19-doxydocs/structPaStreamCallbackTimeInfo.html
- https://portaudio.com/docs/v19-doxydocs/api_overview.html (callback restrictions)
