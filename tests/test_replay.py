import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.replay_timing import replay
from test_ptp import SOURCE, message


class ReplayTests(unittest.TestCase):
    def test_packet_capture_to_clock_mapping_and_duplicate_suppression(self):
        with tempfile.TemporaryDirectory() as folder:
            capture = Path(folder)/'test.jsonl'
            rows = []
            for seq in range(50):
                for kind, delay in ((0, 100_000), (8, 200_000), (8, 300_000)):
                    rows.append(dict(clock='perf_counter_ns', received_ns=seq*125_000_000+delay,
                                packet_hex=message(kind, seq, origin=10**18+seq*125_000_000).hex()))
            capture.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
            report = replay(capture, source=SOURCE, master_id=123, max_receive_delay_ns=200_000)
            self.assertEqual(report['matched'], 50)
            self.assertEqual(report['malformed'], 0)
            self.assertGreater(report['fitted_mappings'], 10)
            self.assertEqual(len(report['sources']), 1)
            self.assertTrue(report['delay_bound_is_assumed'])

    def test_no_clock_without_declared_delay_and_no_false_success_on_empty_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            capture = Path(folder)/'empty.jsonl'; capture.write_text('')
            self.assertEqual(replay(capture)['matched'], 0)
            with self.assertRaises(ValueError): replay(capture, source=SOURCE, master_id=123)

    def test_invalid_record_shapes_and_clock_domains_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            capture = Path(folder)/'invalid.jsonl'
            for value in (None, [], 3, {}, {'packet_hex':0, 'received_ns':0}, {'packet_hex':'', 'received_ns':True}):
                capture.write_text(json.dumps(value))
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'line 1'):
                    replay(capture)
            capture.write_text(json.dumps(dict(packet_hex=message().hex(), received_ns=1,
                                               clock='monotonic_ns')))
            with self.assertRaisesRegex(ValueError, 'epochs must not be mixed'):
                replay(capture, source=SOURCE, master_id=123, max_receive_delay_ns=200_000)
