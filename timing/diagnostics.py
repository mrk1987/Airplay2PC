"""Opt-in, private anchor-only logging. Never records keys, media or full plists."""
import json
import os
from pathlib import Path
import threading
from .anchors import BufferedAnchor, RealtimeAnchor
from .clock import CLOCK_NAME, now_ns

_lock = threading.Lock()
_FIELDS = ('networkTimeTimelineID', 'rtpTime', 'networkTimeSecs', 'networkTimeFrac', 'rate')


def _write(record):
    directory = os.environ.get('AIRPLAY_TIMING_LOG_DIR')
    if not directory:
        return
    try:
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'anchors-{os.getpid()}.jsonl'
        record['received_ns'] = now_ns()
        record['clock'] = CLOCK_NAME
        with _lock:
            if path.exists() and path.stat().st_size >= 5_000_000:
                return  # diagnostics must not fill the disk or interfere with playback
            with path.open('a', encoding='utf-8') as output:
                output.write(json.dumps(record)+'\n')
    except OSError:
        pass  # diagnostics failures must never abort playback


def observe_buffered(payload):
    if not os.environ.get('AIRPLAY_TIMING_LOG_DIR'):
        return
    if not isinstance(payload, dict):
        return
    # Pick only small numeric fields. Unknown/missing data is recorded as absent.
    safe = {key: payload[key] for key in _FIELDS if key in payload
            and type(payload[key]) in (int, float) and 0 <= payload[key] < 2**64}
    try:
        BufferedAnchor.from_plist(safe)
        valid = True
    except (ValueError, KeyError):
        valid = False
    _write(dict(kind='buffered', fields=safe, validated=valid))


def observe_realtime(data):
    if not os.environ.get('AIRPLAY_TIMING_LOG_DIR'):
        return
    if not isinstance(data, (bytes, bytearray)):
        return
    try:
        anchor = RealtimeAnchor.from_rtcp(data)
    except ValueError:
        return
    _write(dict(kind='realtime', sender_rtp=anchor.sender_rtp,
                presentation_rtp=anchor.presentation_rtp, network_ns=anchor.network_ns,
                master_id=anchor.master_id, latency_samples=anchor.latency_samples))
