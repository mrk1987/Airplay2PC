"""Replay private probe JSONL captures without opening sockets or audio hardware."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.ptp import SyncMatcher
from timing.follower import ClockFollower
from timing.timeline import TimingUnavailable
from timing.clock import CLOCK_NAME


def replay(path, *, source=None, master_id=None, max_receive_delay_ns=None):
    if source is None and (master_id is not None or max_receive_delay_ns is not None):
        raise ValueError('Source, master ID and delay assumption must be supplied together')
    if source is not None and (master_id is None or max_receive_delay_ns is None):
        raise ValueError('Clock fitting requires explicit master ID and receive-delay assumption')
    matcher = SyncMatcher()
    follower = None
    sources = set()
    matched = malformed = mappings = 0
    worst_uncertainty = 0
    with Path(path).open(encoding='utf-8') as capture:
        for line_number, line in enumerate(capture, 1):
            if len(line) > 10000:
                raise ValueError(f'Oversized record at line {line_number}')
            record = json.loads(line)
            if (not isinstance(record, dict) or not isinstance(record.get('packet_hex'), str)
                    or type(record.get('received_ns')) is not int or record['received_ns'] < 0):
                raise ValueError(f'Invalid packet record at line {line_number}')
            if source is not None and record.get('clock') != CLOCK_NAME:
                raise ValueError('Fitting requires explicit perf_counter_ns timestamps; clock epochs must not be mixed')
            try:
                observation = matcher.feed(bytes.fromhex(record['packet_hex']), record['received_ns'])
            except ValueError:
                malformed += 1
                continue
            if observation is None:
                continue
            matched += 1
            sources.add((observation.source.hex(), observation.domain, observation.transport))
            if source is not None and observation.source == source:
                if follower is None:
                    follower = ClockFollower(source, master_id, domain=observation.domain,
                               transport=observation.transport, max_receive_delay_ns=max_receive_delay_ns)
                if follower.observe(observation):
                    try:
                        mapping = follower.mapping(observation.received_ns)
                        mappings += 1
                        worst_uncertainty = max(worst_uncertainty, mapping.uncertainty_ns)
                    except TimingUnavailable:
                        pass
    return dict(matched=matched, malformed=malformed, sources=sorted(sources),
                fitted_mappings=mappings, worst_uncertainty_ns=worst_uncertainty,
                delay_bound_is_assumed=max_receive_delay_ns is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--source', help='20 hex digits: PTP clockIdentity plus portNumber')
    parser.add_argument('--master-id', type=lambda text: int(text, 16))
    parser.add_argument('--assumed-max-delay-us', type=int)
    args = parser.parse_args()
    try:
        source = bytes.fromhex(args.source) if args.source else None
        delay = args.assumed_max_delay_us*1000 if args.assumed_max_delay_us is not None else None
        result = replay(args.capture, source=source, master_id=args.master_id, max_receive_delay_ns=delay)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    print('Diagnostic replay only. No audio alignment or measured path-delay claim.')
    return 0 if result['matched'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
