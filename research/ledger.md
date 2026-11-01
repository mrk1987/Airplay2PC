# Evidence ledger — 2026-11-02

| ID | Claim | Verdict | Evidence |
|---|---|---|---|
| H1 | Whole PyAV audio plane is valid PCM | Invalidated | Local 352-sample conversion: 1408 valid vs 1536 allocated; earlier live logs match. |
| H2 | Fixes restore clean audible playback | Validated for current session | Andreas: "holy shit i think you did it. sounds clean now." Longer run not measured. |
| H3 | Current implementation accurately syncs AirPlay rooms | Invalidated as implementation claim; audible alignment unmeasured | Upstream README; SETRATEANCHORTIME drops network anchor; player uses local receipt time. |
| H4 | goplay2 is a ready Windows alternative | Invalidated | Primary README excludes Windows, ALAC and realtime Spotify. |
| H5 | Shairport Sync Cygwin supports AirPlay 2 | Invalidated | Official CYGWIN.md explicitly excludes it. |
| H6 | AirServer Windows supports this exact grouped playback | Insufficient evidence | Connect hardware specification does not establish Windows software capability. |
| H7 | Windows can observe live group PTP on this LAN | Needs local test | Passive bind/join succeeds; idle 8-second probe saw no packets. Active group not established during probe. |

Round 1: Retain receiver after measured padding fix and successful user listening test.
Defer new timing implementation pending acoustic group test. This follows the user's
clarification that robotic/rubber-banding sound is the immediate problem.

Volume follow-up: commands selected the control-process PID, which owns no Windows audio session. Changed both realtime and buffered SETUP paths to the data/playback PID. Restarted native receiver; Andreas confirmed iPhone volume follows on PC.
