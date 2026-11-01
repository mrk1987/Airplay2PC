import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.diagnostics import observe_buffered, observe_realtime


class DiagnosticTests(unittest.TestCase):
    def test_only_safe_fields_are_recorded(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AIRPLAY_TIMING_LOG_DIR': folder}):
            observe_buffered(dict(rate=1, rtpTime=0, networkTimeTimelineID=123,
                                  networkTimeSecs=10, networkTimeFrac=2**63,
                                  session_key='must-not-be-recorded', unknown='private'))
            rows = [json.loads(line) for p in Path(folder).glob('*.jsonl') for line in p.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]['validated'])
            self.assertNotIn('must-not-be-recorded', json.dumps(rows))
            self.assertEqual(set(rows[0]['fields']), {'rate','rtpTime','networkTimeTimelineID','networkTimeSecs','networkTimeFrac'})

    def test_disabled_and_invalid_observations_do_not_crash(self):
        with patch.dict(os.environ, {'AIRPLAY_TIMING_LOG_DIR': ''}):
            observe_buffered({})
            observe_realtime(b'')
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AIRPLAY_TIMING_LOG_DIR': folder}):
            observe_buffered({'rate':0, 'rtpTime':True})
            observe_realtime(b'')
            row = json.loads(next(Path(folder).glob('*.jsonl')).read_text())
            self.assertFalse(row['validated'])

    def test_io_failure_is_contained(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AIRPLAY_TIMING_LOG_DIR': folder}), patch('pathlib.Path.open', side_effect=OSError('unwritable')):
            observe_buffered({'rate':0})
