"""Bounded PTPv2 Sync/FollowUp decoder. No master election or socket ownership.

The paired observation uses the Sync receive timestamp, not FollowUp arrival.
Correction fields retain signed 2**-16 nanosecond precision. A receive timestamp
still includes unknown path/host delay: observations are not calibrated clocks.
"""
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction

from .timeline import _integers


@dataclass(frozen=True)
class PtpMessage:
    kind: int
    transport: int
    domain: int
    source: bytes  # clockIdentity + portNumber, not necessarily grandmaster ID
    sequence: int
    two_step: bool
    correction_ns: Fraction
    origin_ns: int | None

    @property
    def key(self):
        return self.transport, self.domain, self.source, self.sequence


def parse_ptp(data: bytes) -> PtpMessage:
    if len(data) < 34 or data[1] & 15 != 2:
        raise ValueError('Truncated or non-PTPv2 header')
    length = int.from_bytes(data[2:4], 'big')
    if not 34 <= length <= len(data):
        raise ValueError('Invalid PTP messageLength')
    kind = data[0] & 15
    origin = None
    if kind in (0, 8):
        if length < 44:
            raise ValueError('Truncated Sync/FollowUp timestamp')
        nanos = int.from_bytes(data[40:44], 'big')
        if nanos >= 1_000_000_000:
            raise ValueError('Invalid PTP nanoseconds')
        origin = int.from_bytes(data[34:40], 'big') * 1_000_000_000 + nanos
    correction = int.from_bytes(data[8:16], 'big', signed=True)
    if correction == 2**63 - 1:
        raise ValueError('PTP correction overflow sentinel')
    return PtpMessage(kind, data[0] >> 4, data[4], bytes(data[20:30]),
                      int.from_bytes(data[30:32], 'big'), bool(data[6] & 2),
                      Fraction(correction, 65536), origin)


@dataclass(frozen=True)
class Observation:
    source: bytes
    domain: int
    transport: int
    sequence: int
    received_ns: int
    master_at_send_ns: Fraction


class SyncMatcher:
    """Bound memory/time, match either arrival order, suppress recent duplicates.

    Single-thread owner. Caller must filter allowed peers and select its master;
    packets from different sources are never used interchangeably.
    """
    def __init__(self, capacity=256, ttl_ns=1_000_000_000):
        _integers(capacity, ttl_ns)
        if capacity < 1 or ttl_ns < 1:
            raise ValueError('Capacity and TTL must be positive')
        self.capacity, self.ttl_ns = capacity, ttl_ns
        self.pending = OrderedDict()
        self.completed = OrderedDict()
        self.last_received_ns = -1

    def feed(self, data: bytes, received_ns: int) -> Observation | None:
        _integers(received_ns)
        if received_ns < 0 or received_ns < self.last_received_ns:
            raise ValueError('Receive clock must be nonnegative and monotonic')
        self.last_received_ns = received_ns
        for table in (self.pending, self.completed):
            for key, value in list(table.items()):
                stamp = value[0] if table is self.pending else value
                if received_ns - stamp >= self.ttl_ns:
                    del table[key]
        msg = parse_ptp(data)
        if msg.kind not in (0, 8) or msg.key in self.completed:
            return None
        if msg.kind == 0 and not msg.two_step:
            self.pending.pop(msg.key, None)
            return self._finish(msg, received_ns, msg.origin_ns + msg.correction_ns, received_ns)
        entry = self.pending.get(msg.key)
        if entry is None:
            entry = (received_ns, {})
            self.pending[msg.key] = entry
        pieces = entry[1]
        # First copy wins: duplicate traffic must not move the receive timestamp.
        pieces.setdefault(msg.kind, (msg, received_ns))
        while len(self.pending) > self.capacity:
            self.pending.popitem(last=False)
        if 0 not in pieces or 8 not in pieces:
            return None
        sync, stamp = pieces[0]
        follow, _ = pieces[8]
        self.pending.pop(msg.key, None)
        master = follow.origin_ns + sync.correction_ns + follow.correction_ns
        return self._finish(sync, stamp, master, received_ns)

    def _finish(self, msg, sync_received_ns, master_ns, completed_ns):
        self.completed[msg.key] = completed_ns
        while len(self.completed) > self.capacity:
            self.completed.popitem(last=False)
        return Observation(msg.source, msg.domain, msg.transport, msg.sequence,
                           sync_received_ns, master_ns)
