"""Offline scheduling policy. A real DAC backend must execute these decisions."""
from dataclasses import dataclass
from fractions import Fraction
from .timeline import TimingUnavailable, _integers


@dataclass(frozen=True)
class Decision:
    deadline_ns: int
    speed_ppm: Fraction  # positive consumes source samples faster


class DriftController:
    """Bounded proportional correction, explicit discontinuity rejection.

    Positive error means audio is late. Rate correction is limited to 200 ppm
    by default, slewed at 20 ppm/sec; it must drive a continuous resampler, never
    a sleep interval or repeated/dropped PCM blocks. These are pilot parameters.
    """
    def __init__(self, max_ppm=200, slew_ppm_per_second=20, horizon_ns=10_000_000_000,
                 discontinuity_ns=20_000_000):
        _integers(max_ppm, slew_ppm_per_second, horizon_ns, discontinuity_ns)
        if min(max_ppm, slew_ppm_per_second, horizon_ns, discontinuity_ns) <= 0:
            raise ValueError('Controller bounds must be positive')
        self.max_ppm, self.slew = max_ppm, slew_ppm_per_second
        self.horizon, self.discontinuity = horizon_ns, discontinuity_ns
        self.reset()

    def reset(self):
        self.last_ns = None
        self.speed_ppm = Fraction(0)

    def update(self, error_ns, now_ns):
        _integers(error_ns, now_ns)
        if now_ns < 0 or (self.last_ns is not None and now_ns <= self.last_ns):
            raise ValueError('Controller clock must advance')
        if abs(error_ns) >= self.discontinuity:
            self.reset()
            raise TimingUnavailable('Discontinuity requires rebuffer/reanchor')
        desired = max(-self.max_ppm, min(self.max_ppm, Fraction(error_ns*1_000_000, self.horizon)))
        if self.last_ns is not None:
            allowance = Fraction((now_ns-self.last_ns)*self.slew, 10**9)
            self.speed_ppm += max(-allowance, min(allowance, desired-self.speed_ppm))
        # First observation establishes time with zero correction.
        self.last_ns = now_ns
        return self.speed_ppm


class Scheduler:
    def __init__(self):
        self.anchor = None
        self.drift = DriftController()

    def set_anchor(self, anchor):
        self.anchor = anchor
        self.drift.reset()  # includes seek/reanchor even under the same master

    def pause(self):
        self.anchor = None
        self.drift.reset()

    def plan(self, timestamp, clock, *, now_ns, output_latency_ns, phase_error_ns,
             max_uncertainty_ns):
        if self.anchor is None:
            raise TimingUnavailable('No active anchor')
        try:
            deadline = self.anchor.write_deadline(timestamp, clock, now_ns=now_ns,
                       output_latency_ns=output_latency_ns, max_uncertainty_ns=max_uncertainty_ns)
            correction = self.drift.update(phase_error_ns, now_ns)
            return Decision(deadline, correction)
        except (TimingUnavailable, ValueError):
            self.pause()  # fail closed: no automatic stale-anchor reuse
            raise
