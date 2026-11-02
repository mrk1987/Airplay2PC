"""Fixed s16 PCM delay line. Same bytes per write; no rate change or sleeps."""


class PcmDelay:
    def __init__(self, milliseconds, sample_rate, channels):
        if any(type(value) is not int for value in (milliseconds, sample_rate, channels)):
            raise ValueError('Delay, sample rate and channels must be integers')
        if not 0 <= milliseconds <= 2000 or not 8000 <= sample_rate <= 192000 or channels not in (1, 2):
            raise ValueError('Invalid output delay parameters')
        self.frame_bytes = channels*2
        self.size = ((sample_rate*milliseconds+500)//1000)*self.frame_bytes
        self.pending = bytes(self.size)

    def process(self, data):
        if len(data) % self.frame_bytes:
            raise ValueError('PCM must contain complete sample frames')
        if not self.size:
            return data
        combined = self.pending + data
        result, self.pending = combined[:len(data)], combined[len(data):]
        return result
