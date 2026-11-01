"""Experimental fit of a selected clock's raw observations.

The declared receive-delay ceiling is a test assumption, NOT measured by this
class. Production use requires validating it on the actual Windows host/LAN.
"""
from collections import deque
from fractions import Fraction
from .timeline import ClockIdentity, ClockMapping, TimingUnavailable, _integers


class ClockFollower:
    def __init__(self, source: bytes, master_id: int, *, domain=0, transport=0,
                 max_receive_delay_ns: int, ttl_ns=2_000_000_000,
                 max_rate_error_ppm=500, window=32):
        _integers(max_receive_delay_ns, ttl_ns, max_rate_error_ppm, window, transport)
        ClockIdentity(master_id, domain, 0)
        if len(source) != 10 or not 0 <= transport < 16:
            raise ValueError('Expected PTP source port identity and transport nibble')
        if max_receive_delay_ns < 0 or ttl_ns <= 0 or max_rate_error_ppm <= 0 or window < 8:
            raise ValueError('Invalid follower bounds')
        self.source, self.master_id, self.domain, self.transport = source, master_id, domain, transport
        self.delay = max_receive_delay_ns
        self.ttl, self.max_ppm = ttl_ns, max_rate_error_ppm
        self.samples = deque(maxlen=window)
        self.minimum_spacing = (2_000_000_000 + window-2)//(window-1)
        self.generation = 0

    def reset(self):
        self.samples.clear()
        self.generation += 1

    def observe(self, observation):
        if (observation.source, observation.domain, observation.transport) != (self.source, self.domain, self.transport):
            return False
        local, master = observation.received_ns, observation.master_at_send_ns
        if self.samples:
            previous_local, previous_master = self.samples[-1]
            if local <= previous_local:
                return False
            if local - previous_local >= self.ttl or master <= previous_master:
                self.reset()
            elif abs((master-previous_master)-(local-previous_local)) > self.delay + Fraction((local-previous_local)*self.max_ppm, 1_000_000):
                self.reset()  # forward clock step invalidates anchors too
            elif local - previous_local < self.minimum_spacing:
                return False  # retain two seconds even with high-rate Sync packets
        # Centre the allowed receive delay. Its unknown half-range is in uncertainty.
        self.samples.append((local, master))
        return True

    def mapping(self, now_ns):
        _integers(now_ns)
        if not self.samples:
            raise TimingUnavailable('No selected-clock observations')
        latest = self.samples[-1][0]
        if now_ns >= latest + self.ttl:
            self.reset()
            raise TimingUnavailable('Timing expired; reacquisition required')
        if now_ns < latest or len(self.samples) < 8:
            raise TimingUnavailable('Clock is warming up or observation is in the future')
        x0, y0 = self.samples[0]
        if latest - x0 < 2_000_000_000:
            raise TimingUnavailable('Need at least two seconds of clock history')
        xs = [x-x0 for x, _ in self.samples]
        ys = [y-y0 for _, y in self.samples]
        count = len(xs)
        denominator = count*sum(x*x for x in xs) - sum(xs)**2
        rate = Fraction(count*sum(x*y for x, y in zip(xs, ys))-sum(xs)*sum(ys), denominator)
        if abs(rate - 1)*1_000_000 > self.max_ppm:
            raise TimingUnavailable('Implausible fitted clock rate')
        intercept = Fraction(sum(ys)-rate*sum(xs), count)
        residual = max(abs(y-(intercept+rate*x)) for x, y in zip(xs, ys))
        if residual > self.delay:
            raise TimingUnavailable('Receive jitter exceeds declared delay budget')
        # Conservative full-horizon allowance, including allowed oscillator drift.
        uncertainty = self.delay + int(residual.__ceil__()) + (2*self.ttl*self.max_ppm+999_999)//1_000_000
        master = round(y0 + intercept + rate*(latest-x0) + Fraction(self.delay, 2))
        return ClockMapping(ClockIdentity(self.master_id, self.domain, self.generation),
                            latest, master, rate, latest+self.ttl, uncertainty)
