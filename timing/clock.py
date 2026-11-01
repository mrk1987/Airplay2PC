"""One high-resolution local timebase for the experimental pipeline.

On Windows Python 3.12, monotonic_ns uses GetTickCount64 (~15.6 ms).
perf_counter_ns uses QueryPerformanceCounter. Never mix their epochs.
"""
import time

CLOCK_NAME = 'perf_counter_ns'


def validate_clock():
    info = time.get_clock_info('perf_counter')
    if not info.monotonic or info.adjustable or info.resolution > 1e-6:
        raise RuntimeError('Experimental timing requires a monotonic clock with <=1 us resolution')
    return info


now_ns = time.perf_counter_ns
