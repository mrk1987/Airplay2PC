"""Regression tests: no network, pairing credentials or audio hardware needed."""
import logging
import struct
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'airplay2-receiver'))
import av
from ap2.connections.audio import Audio, AirplayAudFmt, RTPRealtimeBuffer


def packet(seq):
    return SimpleNamespace(sequence_no=seq, timestamp=(seq * 352) & 0xffffffff)


class BufferTests(unittest.TestCase):
    def test_pop_keeps_indexes_and_accepts_zero(self):
        b = RTPRealtimeBuffer(20)
        for n in (65535, 0, 1): b.append(packet(n))
        self.assertEqual(b.pop(0).sequence_no, 0)
        self.assertEqual(list(b.sn_queue), [1, 65535])
        self.assertEqual(list(b.ts_queue), [352, 65535 * 352])
        self.assertEqual(b.pop(65535).sequence_no, 65535)
        self.assertEqual(b.pop().sequence_no, 1)
        self.assertFalse(b.ts_queue)

    def test_flush_empty_and_rollover_preserves_order(self):
        b = RTPRealtimeBuffer(20)
        b.flush(0)
        for n in (65534, 65535, 0, 1): b.append(packet(n))
        b.flush(65535)
        self.assertEqual([b.pop().sequence_no for _ in range(3)], [65535, 0, 1])
        self.assertFalse(b.sn_queue)
        self.assertFalse(b.ts_queue)

    def test_gap_skips_forward_in_sequence_order_not_arrival_order(self):
        b = RTPRealtimeBuffer(20)
        for n in (65534, 2, 1, 65535): b.append(packet(n))
        self.assertEqual(b.pop_next(65535).sequence_no, 1)
        self.assertEqual(b.pop_next(1).sequence_no, 2)
        self.assertIsNone(b.pop_next(2))
        self.assertFalse(b.ts_queue)

    def test_small_buffer_and_timestamp_wrap(self):
        b = RTPRealtimeBuffer(2)
        b.append(SimpleNamespace(sequence_no=1, timestamp=0xffffff00))
        b.append(SimpleNamespace(sequence_no=2, timestamp=96))
        self.assertEqual(b.ts_diff, 352)


class DecodeTests(unittest.TestCase):
    def test_all_advertised_sample_rates_and_channels(self):
        for fmt in AirplayAudFmt:
            with self.subTest(fmt=fmt.name):
                audio = SimpleNamespace(audio_screen_logger=logging.getLogger('test'))
                Audio.set_audio_params(audio, fmt.value)
                self.assertEqual(audio.sample_rate, int(fmt.name.split('_')[-3 if '_16_' in fmt.name or '_24_' in fmt.name else -2]))
                self.assertEqual(audio.channel_count, int(fmt.name[-1]))

    def test_real_alac_roundtrip_exact_pcm_no_padding(self):
        for samples in (352, 1024):
            for depth in (16, 24):
                with self.subTest(samples=samples, depth=depth):
                    fmt = 's16p' if depth == 16 else 's32p'
                    enc = av.CodecContext.create('alac', 'w')
                    enc.sample_rate = 44100
                    enc.layout = 'stereo'
                    enc.format = fmt
                    enc.open()
                    f = av.AudioFrame(format=fmt, layout='stereo', samples=samples)
                    f.sample_rate = 44100
                    for ch, plane in enumerate(f.planes):
                        values = [((i * 97 + ch * 1000) % 20000) - 10000 for i in range(samples)]
                        packed = struct.pack('<' + ('h' if depth == 16 else 'i') * samples,
                                             *[v if depth == 16 else v << 16 for v in values])
                        plane.update(packed + bytes(plane.buffer_size - len(packed)))
                    packets = enc.encode(f) + enc.encode(None)
                    self.assertTrue(packets)
                    audio = Audio.__new__(Audio)
                    audio.audio_screen_logger = logging.getLogger('test')
                    audio.codecContext = av.CodecContext.create('alac', 'r')
                    audio.codecContext.extradata = enc.extradata
                    audio.resampler = av.AudioResampler(format='s16', layout='stereo', rate=44100)
                    audio.decrypt = lambda p: bytes(p)
                    pcm = b''.join(audio.process(p) for p in packets)
                    self.assertEqual(len(pcm), samples * 4)
                    expected = b''.join(struct.pack('<hh', ((i * 97) % 20000) - 10000,
                                                    ((i * 97 + 1000) % 20000) - 10000)
                                        for i in range(samples))
                    self.assertEqual(pcm, expected)

    def test_multiple_and_empty_resampler_outputs(self):
        audio = Audio.__new__(Audio)
        audio.decrypt = lambda p: b'encoded'
        audio.audio_screen_logger = logging.getLogger('test')
        audio.codecContext = SimpleNamespace(decode=lambda p: [None, None])
        f = av.AudioFrame(format='s16', layout='stereo', samples=352)
        f.planes[0].update(bytes(f.planes[0].buffer_size))
        outputs = iter([[], [f, f]])
        audio.resampler = SimpleNamespace(resample=lambda f: next(outputs))
        self.assertEqual(len(audio.process(None)), 352 * 4 * 2)

if __name__ == '__main__': unittest.main()
