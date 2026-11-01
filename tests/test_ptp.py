from fractions import Fraction
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.ptp import parse_ptp, SyncMatcher, Observation
from timing.anchors import BufferedAnchor, RealtimeAnchor
from timing.follower import ClockFollower
from timing.timeline import ClockIdentity, TimingUnavailable


SOURCE = bytes.fromhex('0123456789abcdef0001')


def message(kind=0, seq=0, *, origin=10**18, correction=0, two_step=True, domain=0, source=SOURCE):
    data = bytearray(44)
    data[0], data[1], data[4] = kind, 2, domain
    data[2:4] = (44).to_bytes(2, 'big')
    data[6] = 2 if two_step else 0
    data[8:16] = correction.to_bytes(8, 'big', signed=True)
    data[20:30] = source
    data[30:32] = seq.to_bytes(2, 'big')
    data[34:40] = (origin//10**9).to_bytes(6, 'big')
    data[40:44] = (origin%10**9).to_bytes(4, 'big')
    return bytes(data)


class PacketTests(unittest.TestCase):
    def test_pair_exact_correction_and_sync_receipt(self):
        matcher = SyncMatcher()
        self.assertIsNone(matcher.feed(message(correction=-32768), 100))
        observation = matcher.feed(message(8, correction=98304), 200)
        self.assertEqual(observation.master_at_send_ns, 10**18+1)
        self.assertEqual(observation.received_ns, 100)
        self.assertIsNone(matcher.feed(message(8), 201))

    def test_reorder_one_step_and_duplicates(self):
        matcher = SyncMatcher()
        self.assertIsNone(matcher.feed(message(8), 10))
        self.assertEqual(matcher.feed(message(), 20).received_ns, 20)
        matcher = SyncMatcher()
        matcher.feed(message(), 10)
        matcher.feed(message(), 15)
        self.assertEqual(matcher.feed(message(8), 20).received_ns, 10)
        self.assertEqual(matcher.feed(message(seq=1, two_step=False, correction=32768), 30).master_at_send_ns,
                         Fraction(10**18)+Fraction(1, 2))

    def test_identity_isolation_capacity_and_expiry(self):
        matcher = SyncMatcher(capacity=2, ttl_ns=10)
        matcher.feed(message(), 0)
        self.assertIsNone(matcher.feed(message(8, domain=1), 1))
        self.assertIsNone(matcher.feed(message(8, source=b'otherclock'), 2))
        self.assertLessEqual(len(matcher.pending), 2)
        self.assertIsNone(matcher.feed(message(8), 10))  # original Sync expired/evicted
        for n in range(10): matcher.feed(message(seq=n, two_step=False), 11+n)
        self.assertLessEqual(len(matcher.completed), 2)

    def test_malformed_and_backward_receive_time(self):
        for raw in (b'', message()[:40], message()[:1]+b'\x01'+message()[2:]):
            with self.assertRaises(ValueError): parse_ptp(raw)
        raw = bytearray(message()); raw[40:44] = (10**9).to_bytes(4, 'big')
        with self.assertRaises(ValueError): parse_ptp(raw)
        matcher = SyncMatcher(); matcher.feed(message(), 10)
        with self.assertRaises(ValueError): matcher.feed(message(8), 9)

    def test_sequence_wrap(self):
        matcher = SyncMatcher()
        for index, seq in enumerate((65535, 0, 1)):
            matcher.feed(message(seq=seq), index*10)
            self.assertEqual(matcher.feed(message(8, seq=seq), index*10+1).sequence, seq)
            self.assertIsNone(matcher.feed(message(seq=seq), index*10+2))

    def test_overflow_sentinel_truncated_followup_and_ttl_boundary(self):
        with self.assertRaises(ValueError): parse_ptp(message(correction=2**63-1))
        raw = bytearray(message(8)[:40]); raw[2:4] = (40).to_bytes(2, 'big')
        with self.assertRaises(ValueError): parse_ptp(raw)
        matcher = SyncMatcher(ttl_ns=10)
        matcher.feed(message(), 0)
        self.assertIsNone(matcher.feed(message(8), 10))


class AnchorTests(unittest.TestCase):
    def test_binary_fraction_and_clock_identity(self):
        payload = dict(networkTimeTimelineID=123, rtpTime=0, networkTimeSecs=10,
                       networkTimeFrac=2**63, rate=1)
        record = BufferedAnchor.from_plist(payload)
        self.assertEqual(record.bind(ClockIdentity(123, 0, 0), 48000).master_ns, 10_500_000_000)
        with self.assertRaises(ValueError): record.bind(ClockIdentity(124, 0, 0), 48000)
        for key, bad in [('networkTimeFrac', 2**64), ('rtpTime', True), ('rate', 0.5)]:
            with self.assertRaises(ValueError): BufferedAnchor.from_plist(dict(payload, **{key: bad}))

    def test_realtime_keeps_both_counters_and_requires_policy(self):
        raw = bytes.fromhex('90d70006213678190001a403e3be94b52137a5900102030405060708')
        record = RealtimeAnchor.from_rtcp(raw)
        self.assertEqual(record.sender_rtp, 0x21367819)
        self.assertEqual(record.presentation_rtp, 0x2137a590)
        identity = ClockIdentity(0x0102030405060708, 0, 0)
        with self.assertRaises(TypeError): record.bind(identity, 44100)
        self.assertEqual(record.bind(identity, 44100, sender_adjustment_samples=-11025).rtp_timestamp,
                         (record.sender_rtp-11025)&0xffffffff)
        with self.assertRaises(ValueError): RealtimeAnchor.from_rtcp(raw[:20])


class FollowerTests(unittest.TestCase):
    def observation(self, index, *, delay=100_000, rate=Fraction(1), source=SOURCE):
        sent = index*1_000_000_000
        return Observation(source, 0, 0, index%65536, sent+delay, Fraction(10**18)+sent*rate)

    def test_thirty_minute_clock_with_bounded_variable_delay(self):
        follower = ClockFollower(SOURCE, 123, max_receive_delay_ns=200_000)
        rate = Fraction(1_000_050, 1_000_000)
        for index in range(1801):
            delay = 80_000 + (index%5)*10_000
            obs = self.observation(index, delay=delay, rate=rate)
            follower.observe(obs)
            if index >= 7:
                mapping = follower.mapping(obs.received_ns)
                target = obs.received_ns + 500_000_000
                true_master = 10**18 + round(target*rate)
                estimated_local = mapping.local_time(true_master, now_ns=obs.received_ns,
                                  identity=mapping.identity, max_uncertainty_ns=3_000_000)
                self.assertLess(abs(estimated_local-target), mapping.uncertainty_ns)

    def test_stale_reacquisition_and_source_selection(self):
        follower = ClockFollower(SOURCE, 123, max_receive_delay_ns=200_000)
        self.assertFalse(follower.observe(self.observation(0, source=b'otherclock')))
        for n in range(8): follower.observe(self.observation(n))
        old = follower.mapping(7_000_100_000)
        with self.assertRaises(TimingUnavailable): follower.mapping(10_000_000_000)
        for n in range(11, 19): follower.observe(self.observation(n))
        self.assertNotEqual(follower.mapping(18_000_100_000).identity, old.identity)

    def test_rate_outside_budget_and_insufficient_history(self):
        follower = ClockFollower(SOURCE, 123, max_receive_delay_ns=200_000)
        follower.observe(self.observation(0))
        with self.assertRaises(TimingUnavailable): follower.mapping(100_000)
        for n in range(1, 8): follower.observe(self.observation(n, rate=Fraction(2)))
        with self.assertRaises(TimingUnavailable): follower.mapping(7_000_100_000)

    def test_forward_step_invalidates_generation(self):
        follower = ClockFollower(SOURCE, 123, max_receive_delay_ns=200_000)
        for n in range(8): follower.observe(self.observation(n))
        identity = follower.mapping(7_000_100_000).identity
        obs = self.observation(8)
        jumped = Observation(obs.source, obs.domain, obs.transport, obs.sequence,
                             obs.received_ns, obs.master_at_send_ns + 10**9)
        follower.observe(jumped)
        self.assertNotEqual(follower.generation, identity.generation)
        with self.assertRaises(TimingUnavailable): follower.mapping(obs.received_ns)

    def test_fifty_ms_sync_spacing_can_warm_up(self):
        follower = ClockFollower(SOURCE, 123, max_receive_delay_ns=200_000)
        for n in range(100):
            t = n*50_000_000
            follower.observe(Observation(SOURCE, 0, 0, n, t+100_000, Fraction(10**18+t)))
        mapping = follower.mapping(4_950_100_000)
        self.assertLessEqual(len(follower.samples), 32)
        self.assertLess(mapping.uncertainty_ns, 3_000_000)


if __name__ == '__main__': unittest.main()
