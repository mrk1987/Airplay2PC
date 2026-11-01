# Timing implementation progress

## Implemented: offline clock and sample timeline

`timing/timeline.py` is experimental and is not imported by receiver playback.
It provides immutable clock identities (master, domain and reacquisition generation),
bounded clock mappings, RTP wrap-aware sample anchors, and audio submission deadlines.
Fraction arithmetic avoids converting large nanosecond epochs to floating point.
The caller supplies a clock rate, uncertainty budget and actual output latency.
Invalid, stale, ambiguous or late scheduling requests fail explicitly.

Eight synthetic tests cover rollover including zero, identity changes, expiry,
uncertainty, latency deadlines, positive/negative drift, pause, rate changes,
replacement anchors and malformed inputs. The 30-minute synthetic conversion
checks arithmetic, not estimated clock accuracy or real audio drift.

No PTP follower, path-delay estimator, protocol anchor parser, scheduler or drift
controller is implemented yet. A supplied clock mapping is a calibration contract,
not a claim that raw Sync/FollowUp receipt times meet that contract. The uncertainty
bound must cover the mapping's entire validity interval, including drift error.
Clock generations must change after reacquisition even when master ID is unchanged.
Anchors must be refreshed before their RTP distance becomes ambiguous (half a cycle).

## Next implementation steps

1. Build replayable PTP fixtures and a bounded parser/matcher for Sync/FollowUp,
   correction fields, source port/domain/sequence and clock changes. Receive timestamps
   alone cannot establish unbiased master time. Validate against NQPTP behavior;
   decide and test path-delay handling before claiming accuracy.
2. Preserve and validate the complete SETRATEANCHORTIME and realtime control anchors.
   Verify timestamp representation, clock identity and units from protocol evidence.
3. Feed clock/anchor observations through a diagnostic-only path. Reject stale data;
   do not change normal playback until that path is validated.
4. Implement backend output-time measurement, scheduling and gradual drift correction
   behind an opt-in experimental mode. Test starvation, pause/seek, reconnect and
   master changes, then perform the daytime acoustic gates in validation.md.

## Local inference review

A local llama-compatible server reviewed the arithmetic for missing boundary tests.
Its suggestions were checked manually: two alleged issues were contradicted by the
code/tests. The useful missing case was negative sample distance at half playback
speed; that case and a slower master clock now have regression coverage. Raw review
output stays local in `archive/model-review/timing-boundaries.txt`.

Reference: https://github.com/mikebrady/nqptp
