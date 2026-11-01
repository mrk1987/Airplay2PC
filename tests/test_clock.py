from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.clock import now_ns, validate_clock


class ClockTests(unittest.TestCase):
    def test_actual_high_resolution_clock(self):
        self.assertLessEqual(validate_clock().resolution, 1e-6)
        before = now_ns()
        self.assertGreaterEqual(now_ns(), before)

    def test_coarse_or_adjustable_clock_rejected(self):
        for resolution, adjustable in ((0.015625, False), (1e-7, True)):
            info = SimpleNamespace(monotonic=True, adjustable=adjustable, resolution=resolution)
            with patch('time.get_clock_info', return_value=info), self.assertRaises(RuntimeError):
                validate_clock()
