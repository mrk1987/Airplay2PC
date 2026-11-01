"""Lossless protocol anchor records. Realtime latency policy remains explicit."""
from dataclasses import dataclass
from fractions import Fraction
from .timeline import ClockIdentity, PlaybackAnchor, _integers


def _uint(value, bits):
    _integers(value)
    if not 0 <= value < 1 << bits:
        raise ValueError(f'Expected uint{bits}')
    return value


@dataclass(frozen=True)
class BufferedAnchor:
    master_id: int
    rtp_timestamp: int
    seconds: int
    fraction: int
    rate: Fraction

    @classmethod
    def from_plist(cls, payload):
        # Require an explicit timeline ID; do not silently pick another clock.
        master = _uint(payload['networkTimeTimelineID'], 64)
        rtp = _uint(payload['rtpTime'], 32)
        secs = _uint(payload['networkTimeSecs'], 64)
        frac = _uint(payload['networkTimeFrac'], 64)
        rate = payload['rate']
        if type(rate) not in (int, float) or rate not in (0, 1):
            raise ValueError('Only protocol play/pause rates are verified')
        return cls(master, rtp, secs, frac, Fraction(rate))

    def bind(self, identity: ClockIdentity, sample_rate: int) -> PlaybackAnchor:
        if identity.master_id != self.master_id:
            raise ValueError('Anchor names a different master clock')
        nanos = self.seconds * 10**9 + self.fraction * 10**9 // 2**64
        return PlaybackAnchor(identity, self.rtp_timestamp, nanos, sample_rate, self.rate)


@dataclass(frozen=True)
class RealtimeAnchor:
    sender_rtp: int
    network_ns: int
    presentation_rtp: int
    master_id: int

    @classmethod
    def from_rtcp(cls, data):
        if len(data) != 28 or data[0] >> 6 != 2 or data[0] & 0x20 or data[1] != 0xd7:
            raise ValueError('Expected unpadded 28-byte AirPlay PTP control packet')
        if int.from_bytes(data[2:4], 'big') != 6:
            raise ValueError('Invalid RTCP length')
        return cls(int.from_bytes(data[4:8], 'big'), int.from_bytes(data[8:16], 'big'),
                   int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:28], 'big'))

    @property
    def latency_samples(self):
        return (self.presentation_rtp - self.sender_rtp) & 0xffffffff

    def bind(self, identity, sample_rate, *, sender_adjustment_samples):
        """Require measured policy; never silently copy another player's fudge."""
        _integers(sender_adjustment_samples)
        if identity.master_id != self.master_id:
            raise ValueError('Anchor names a different master clock')
        return PlaybackAnchor(identity, (self.sender_rtp + sender_adjustment_samples) & 0xffffffff,
                              self.network_ns, sample_rate)
