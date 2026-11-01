from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.output_clock import OutputClock, seconds_to_ns
from timing.timeline import TimingUnavailable


class OutputClockTests(unittest.TestCase):
    def test_dac_timestamp_bridge_and_restart(self):
        mapping = OutputClock.calibrate(10**12-100, 100.0, 10**12+100, generation=1)
        self.assertEqual(mapping.dac_time(100.125, now_ns=10**12, generation=1,
                         max_uncertainty_ns=600000), 10**12+125_000_000)
        with self.assertRaises(TimingUnavailable):
            mapping.dac_time(100.125, now_ns=10**12, generation=2, max_uncertainty_ns=600000)

    def test_bad_clock_measurements_and_expiry(self):
        with self.assertRaises(TimingUnavailable): OutputClock.calibrate(0, 0, 2_000_000, generation=0)
        for value in (float('nan'), float('inf'), -1, True):
            with self.assertRaises(ValueError): seconds_to_ns(value)
        mapping = OutputClock.calibrate(0, 0, 0, generation=0)
        with self.assertRaises(TimingUnavailable):
            mapping.dac_time(2, now_ns=10**9, generation=0, max_uncertainty_ns=10**9)
