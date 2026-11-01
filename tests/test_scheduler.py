from fractions import Fraction
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.scheduler import DriftController, Scheduler
from timing.timeline import ClockIdentity, ClockMapping, PlaybackAnchor, TimingUnavailable


class SchedulerTests(unittest.TestCase):
    def test_simulated_thirty_minute_drift_control(self):
        for hardware_drift in (-100, 100):
            with self.subTest(hardware_drift=hardware_drift):
                controller = DriftController()
                error = Fraction(1_000_000)
                worst = abs(error)
                for second in range(1801):
                    speed = controller.update(round(error), second*10**9)
                    error += hardware_drift*1000 - speed*1000
                    worst = max(worst, abs(error))
                    self.assertLessEqual(abs(speed), 200)
                self.assertLess(worst, 3_000_000)
                self.assertLess(abs(error), 2_000_000)

    def test_slew_discontinuity_and_reset(self):
        controller = DriftController()
        self.assertEqual(controller.update(10_000_000, 0), 0)
        self.assertEqual(controller.update(10_000_000, 10**9), 20)
        with self.assertRaises(TimingUnavailable): controller.update(20_000_000, 2*10**9)
        self.assertEqual(controller.update(0, 3*10**9), 0)

    def test_schedule_pause_clock_change_and_seek(self):
        identity = ClockIdentity(1, 0, 0)
        clock = ClockMapping(identity, 0, 0, Fraction(1), 5*10**9, 0)
        scheduler = Scheduler()
        scheduler.set_anchor(PlaybackAnchor(identity, 0, 10**9, 48000))
        decision = scheduler.plan(0, clock, now_ns=0, output_latency_ns=100_000_000,
                                  phase_error_ns=0, max_uncertainty_ns=0)
        self.assertEqual(decision.deadline_ns, 900_000_000)
        scheduler.pause()
        with self.assertRaises(TimingUnavailable):
            scheduler.plan(0, clock, now_ns=1, output_latency_ns=0, phase_error_ns=0, max_uncertainty_ns=0)
        scheduler.set_anchor(PlaybackAnchor(identity, 0, 10**9, 48000))
        changed = ClockMapping(ClockIdentity(1, 0, 1), 0, 0, Fraction(1), 5*10**9, 0)
        with self.assertRaises(TimingUnavailable):
            scheduler.plan(0, changed, now_ns=1, output_latency_ns=0, phase_error_ns=0, max_uncertainty_ns=0)
        self.assertIsNone(scheduler.anchor)
        scheduler.set_anchor(PlaybackAnchor(changed.identity, 12345, 2*10**9, 48000))
        self.assertEqual(scheduler.plan(12345, changed, now_ns=2, output_latency_ns=0,
                         phase_error_ns=0, max_uncertainty_ns=0).deadline_ns, 2*10**9)
