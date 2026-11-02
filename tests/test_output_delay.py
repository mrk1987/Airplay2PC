from pathlib import Path
import sys
import unittest
import os
import logging
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'vendor/airplay2-receiver'))
from timing.output_delay import PcmDelay


class DelayTests(unittest.TestCase):
    def test_zero_is_exact_identity(self):
        pcm = bytes(range(256))*4
        self.assertIs(PcmDelay(0, 48000, 2).process(pcm), pcm)

    def test_variable_writes_preserve_exact_delayed_stereo_stream(self):
        delay = PcmDelay(10, 48000, 2)
        blocks = [bytes([n])*size for n,size in enumerate((1408,4096,256,8192))]
        output = b''.join(delay.process(block) for block in blocks)
        original = b''.join(blocks)
        self.assertEqual(output, bytes(1920)+original[:-1920])
        self.assertEqual(len(delay.pending),1920)

    def test_reset_is_new_silent_delay_line_and_mono_rounding(self):
        delay = PcmDelay(1,44100,1)
        self.assertEqual(delay.size,88)
        delay.process(b'\x11'*200)
        reset = PcmDelay(1,44100,1)
        self.assertEqual(reset.process(b'\x22'*100),bytes(88)+b'\x22'*12)

    def test_invalid_range_and_incomplete_pcm(self):
        for value in (-1,2001,True,0.5):
            with self.assertRaises(ValueError):PcmDelay(value,48000,2)
        with self.assertRaises(ValueError):PcmDelay(10,48000,2).process(b'123')

    def test_receiver_decoded_pcm_path_consumes_delay_setting(self):
        import av
        from ap2.connections.audio import Audio
        audio = Audio.__new__(Audio)
        audio.sample_rate, audio.channel_count = 48000, 2
        audio.audio_screen_logger = logging.getLogger('delay-test')
        audio.decrypt = lambda _: b'encoded'
        frame = av.AudioFrame(format='s16',layout='stereo',samples=480)
        frame.planes[0].update(b'\x01\x02\x03\x04'*480)
        audio.codecContext = SimpleNamespace(decode=lambda _: [frame])
        audio.resampler = SimpleNamespace(resample=lambda f:[f])
        with patch.dict(os.environ,{'AIRPLAY2PC_OUTPUT_DELAY_MS':'10'}):
            self.assertEqual(audio.process(None),bytes(1920))
            self.assertEqual(audio.process(None),b'\x01\x02\x03\x04'*480)
