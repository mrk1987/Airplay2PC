"""Pure clock/sample conversions; all times are integer nanoseconds.

No network, system-clock adjustment or audio output. Calibration must come from
a separately validated clock follower, not raw packet arrival timestamps.
"""
from dataclasses import dataclass
from fractions import Fraction

NS = 1_000_000_000


class TimingUnavailable(ValueError):
    """A caller must stop scheduling until valid timing is available."""


def _integers(*values):
    if any(type(value) is not int for value in values):
        raise ValueError('Times, counters and budgets must be integers')


def rtp_delta(timestamp: int, anchor: int) -> int:
    """Signed 32-bit sample distance, valid within half a timestamp cycle."""
    _integers(timestamp, anchor)
    if not 0 <= timestamp < 2**32 or not 0 <= anchor < 2**32:
        raise ValueError('RTP timestamps must be unsigned 32-bit integers')
    delta = (timestamp - anchor) & 0xffffffff
    if delta == 2**31:
        raise TimingUnavailable('Ambiguous half-cycle RTP distance')
    return delta if delta < 2**31 else delta - 2**32


@dataclass(frozen=True)
class ClockIdentity:
    master_id: int
    domain: int
    generation: int  # increment on reselection, discontinuity or reacquisition

    def __post_init__(self):
        _integers(self.master_id, self.domain, self.generation)
        if not 0 <= self.master_id < 2**64 or not 0 <= self.domain < 256 or self.generation < 0:
            raise ValueError('Invalid clock identity')


@dataclass(frozen=True)
class ClockMapping:
    identity: ClockIdentity
    local_ns: int
    master_ns: int
    rate: Fraction  # master nanoseconds per local nanosecond
    valid_until_ns: int
    uncertainty_ns: int

    def __post_init__(self):
        _integers(self.local_ns, self.master_ns, self.valid_until_ns, self.uncertainty_ns)
        if not isinstance(self.rate, Fraction) or self.rate <= 0:
            raise ValueError('Clock rate must be a positive Fraction')
        if min(self.local_ns, self.master_ns, self.uncertainty_ns) < 0:
            raise ValueError('Negative time or uncertainty')
        if self.valid_until_ns <= self.local_ns:
            raise ValueError('Clock validity must extend beyond observation')

    def local_time(self, master_ns: int, *, now_ns: int,
                   identity: ClockIdentity, max_uncertainty_ns: int) -> int:
        _integers(master_ns, now_ns, max_uncertainty_ns)
        if identity != self.identity:
            raise TimingUnavailable('Clock identity or generation changed')
        if not self.local_ns <= now_ns < self.valid_until_ns:
            raise TimingUnavailable('Clock estimate is stale or from the future')
        if max_uncertainty_ns < 0 or self.uncertainty_ns > max_uncertainty_ns:
            raise TimingUnavailable('Clock uncertainty exceeds caller budget')
        result = self.local_ns + round(Fraction(master_ns - self.master_ns) / self.rate)
        if not self.local_ns <= result < self.valid_until_ns:
            raise TimingUnavailable('Scheduled output falls outside clock validity')
        return result


@dataclass(frozen=True)
class PlaybackAnchor:
    identity: ClockIdentity
    rtp_timestamp: int
    master_ns: int
    sample_rate: int
    playback_rate: Fraction = Fraction(1)

    def __post_init__(self):
        _integers(self.master_ns, self.sample_rate)
        rtp_delta(self.rtp_timestamp, self.rtp_timestamp)
        if self.master_ns < 0 or self.sample_rate <= 0:
            raise ValueError('Invalid anchor time or sample rate')
        if not isinstance(self.playback_rate, Fraction) or self.playback_rate < 0:
            raise ValueError('Playback rate must be a nonnegative Fraction')

    def presentation_time(self, timestamp: int) -> int:
        if self.playback_rate == 0:
            raise TimingUnavailable('Playback is paused')
        samples = rtp_delta(timestamp, self.rtp_timestamp)
        return self.master_ns + round(Fraction(samples * NS, self.sample_rate) / self.playback_rate)

    def write_deadline(self, timestamp: int, clock: ClockMapping, *, now_ns: int,
                       output_latency_ns: int, max_uncertainty_ns: int) -> int:
        """When to submit a sample, given a measured end-to-end output latency.

        This is a deadline calculation, not a scheduler. The future backend must
        supply actual queued audio/device latency, not blocking write duration.
        """
        _integers(output_latency_ns)
        if output_latency_ns < 0:
            raise ValueError('Negative output latency')
        audible_ns = clock.local_time(self.presentation_time(timestamp), now_ns=now_ns,
                                      identity=self.identity,
                                      max_uncertainty_ns=max_uncertainty_ns)
        deadline = audible_ns - output_latency_ns
        if deadline < now_ns:
            raise TimingUnavailable('Audio submission deadline already missed')
        return deadline
