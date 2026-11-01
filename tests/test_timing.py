"""Synthetic timing tests. No network or speakers are opened."""
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.timeline import ClockIdentity, ClockMapping, PlaybackAnchor, TimingUnavailable, rtp_delta


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.identity = ClockIdentity(123, 0, 1)
        self.clock = ClockMapping(self.identity, 10**12, 10**18, Fraction(1), 10**12 + 5*10**9, 1000)
        self.anchor = PlaybackAnchor(self.identity, 0xffffff00, 10**18 + 10**9, 48000)

    def test_wrap_and_zero_are_valid(self):
        self.assertEqual(rtp_delta(0, 0xffffffff), 1)
        self.assertEqual(rtp_delta(0xffffffff, 0), -1)
        self.assertEqual(self.anchor.presentation_time(0xffffff00), 10**18 + 10**9)
        self.assertEqual(self.anchor.presentation_time(0), 10**18 + 10**9 + round(Fraction(256*10**9, 48000)))
        with self.assertRaises(TimingUnavailable): rtp_delta(2**31, 0)

    def test_latency_and_deadline(self):
        self.assertEqual(self.anchor.write_deadline(0xffffff00, self.clock,
                         now_ns=10**12, output_latency_ns=100_000_000,
                         max_uncertainty_ns=2000), 10**12 + 900_000_000)
        with self.assertRaises(TimingUnavailable):
            self.anchor.write_deadline(0xffffff00, self.clock, now_ns=10**12 + 950_000_000,
                                       output_latency_ns=100_000_000, max_uncertainty_ns=2000)

    def test_clock_reselection_domain_and_staleness(self):
        for identity in (ClockIdentity(124, 0, 1), ClockIdentity(123, 1, 1), ClockIdentity(123, 0, 2)):
            with self.subTest(identity=identity), self.assertRaises(TimingUnavailable):
                self.clock.local_time(10**18, now_ns=10**12, identity=identity, max_uncertainty_ns=2000)
        for now in (10**12-1, self.clock.valid_until_ns):
            with self.assertRaises(TimingUnavailable):
                self.clock.local_time(10**18, now_ns=now, identity=self.identity, max_uncertainty_ns=2000)

    def test_uncertainty_and_future_horizon(self):
        for master, budget in ((10**18, 999), (10**18 + 5*10**9, 2000)):
            with self.assertRaises(TimingUnavailable):
                self.clock.local_time(master, now_ns=10**12, identity=self.identity, max_uncertainty_ns=budget)

    def test_simulated_clock_drift_preserves_large_epoch_precision(self):
        rate = Fraction(1_000_100, 1_000_000)  # +100 ppm
        clock = ClockMapping(self.identity, 10**12, 10**18, rate, 10**12 + 2000*10**9, 0)
        for seconds in (1, 30, 1800):
            elapsed = seconds * 10**9
            self.assertEqual(clock.local_time(10**18 + int(elapsed*rate), now_ns=10**12,
                             identity=self.identity, max_uncertainty_ns=0), 10**12 + elapsed)

    def test_pause_rate_change_and_seek_replace_anchor(self):
        for rate in (Fraction(1), Fraction(2), Fraction(1, 2)):
            anchor = PlaybackAnchor(self.identity, 100, 10**18, 48000, rate)
            self.assertEqual(anchor.presentation_time(48100), 10**18 + round(Fraction(10**9)/rate))
        paused = PlaybackAnchor(self.identity, 100, 10**18, 48000, Fraction(0))
        with self.assertRaises(TimingUnavailable): paused.presentation_time(100)
        sought = PlaybackAnchor(self.identity, 900, 10**18+123, 48000)
        self.assertEqual(sought.presentation_time(900), 10**18+123)

    def test_invalid_inputs(self):
        for value in (-1, 2**32, 1.5, True):
            with self.assertRaises(ValueError): rtp_delta(value, 0)
        with self.assertRaises(ValueError): PlaybackAnchor(self.identity, 0, 0, 0)
        with self.assertRaises(ValueError): ClockMapping(self.identity, 0, 0, Fraction(0), 10, 0)

    def test_past_samples_at_half_speed_and_slow_clock(self):
        anchor = PlaybackAnchor(self.identity, 0, 10**18, 48000, Fraction(1, 2))
        self.assertEqual(anchor.presentation_time(0xffffff00),
                         10**18 - round(Fraction(512*10**9, 48000)))
        clock = ClockMapping(self.identity, 10**12, 10**18, Fraction(9999, 10000),
                             10**12 + 5*10**9, 0)
        self.assertEqual(clock.local_time(10**18 + 999_900_000, now_ns=10**12,
                         identity=self.identity, max_uncertainty_ns=0), 10**12 + 10**9)


if __name__ == '__main__': unittest.main()
