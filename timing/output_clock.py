"""Bridge PortAudio's stream clock to local monotonic time, without opening audio.

Collect bracketed stream.get_time() on a worker thread. Do not call PortAudio
APIs, fit clocks or run this Python policy inside a real-time callback.
"""
from dataclasses import dataclass
from fractions import Fraction
import math
from .timeline import TimingUnavailable, _integers


def seconds_to_ns(seconds):
    if type(seconds) not in (float, int) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Expected finite nonnegative stream time')
    return round(Fraction(seconds)*10**9)


@dataclass(frozen=True)
class OutputClock:
    stream_generation: int
    local_ns: int
    stream_ns: int
    valid_until_ns: int
    uncertainty_ns: int

    @classmethod
    def calibrate(cls, before_ns, stream_seconds, after_ns, *, generation,
                  ttl_ns=1_000_000_000, max_bracket_ns=1_000_000,
                  assumed_rate_error_ppm=500):
        _integers(before_ns, after_ns, generation, ttl_ns, max_bracket_ns, assumed_rate_error_ppm)
        if before_ns < 0 or after_ns < before_ns or generation < 0 or min(ttl_ns, max_bracket_ns) <= 0 or assumed_rate_error_ppm < 0:
            raise ValueError('Invalid output clock bounds')
        width = after_ns-before_ns
        if width > max_bracket_ns:
            raise TimingUnavailable('Stream-clock measurement took too long')
        local = (before_ns+after_ns)//2
        uncertainty = (width+1)//2 + (ttl_ns*assumed_rate_error_ppm+999_999)//1_000_000
        return cls(generation, local, seconds_to_ns(stream_seconds), local+ttl_ns, uncertainty)

    def dac_time(self, output_buffer_dac_seconds, *, now_ns, generation, max_uncertainty_ns):
        _integers(now_ns, generation, max_uncertainty_ns)
        if generation != self.stream_generation or not self.local_ns <= now_ns < self.valid_until_ns:
            raise TimingUnavailable('Stale or restarted audio stream')
        if self.uncertainty_ns > max_uncertainty_ns:
            raise TimingUnavailable('Output clock uncertainty exceeds budget')
        local = self.local_ns + seconds_to_ns(output_buffer_dac_seconds) - self.stream_ns
        if not now_ns <= local < self.valid_until_ns:
            raise TimingUnavailable('DAC timestamp is past or beyond calibration horizon')
        return local
