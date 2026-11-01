"""Passive AirPlay/PTPv2 reachability probe; never adjusts the system clock.

Run while an iPhone is playing to an existing AirPlay 2 group. Offsets are
path-biased observations, NOT synchronisation accuracy measurements.
"""
import argparse
import select
import socket
import time
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from timing.ptp import SyncMatcher, parse_ptp as parse_message
from timing.clock import CLOCK_NAME, now_ns, validate_clock


def parse_ptp(data):
    try:
        msg = parse_message(data)
    except ValueError:
        return None
    return dict(kind=msg.kind, domain=msg.domain, clock=msg.source[:8].hex(),
                source=msg.source.hex(), seq=msg.sequence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface', required=True, help='Local LAN IPv4 address')
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--capture', type=Path, help='Optional private JSONL capture; refuses to overwrite')
    args = parser.parse_args()
    validate_clock()
    if not 0 < args.seconds <= 3600:
        parser.error('--seconds must be between 0 and 3600')
    sockets = []
    counts = {}
    pairs = 0
    matcher = SyncMatcher()
    capture = None
    try:
        if args.capture:
            args.capture.parent.mkdir(parents=True, exist_ok=True)
            capture = args.capture.open('x', encoding='utf-8')
        for port in (319, 320):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sockets.append(s)
            # Exclusive bind: do not steal packets from another timing service.
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            s.bind(('', port))
            membership = socket.inet_aton('224.0.1.129') + socket.inet_aton(args.interface)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        deadline = time.perf_counter() + args.seconds
        while time.perf_counter() < deadline:
            ready, _, _ = select.select(sockets, [], [], min(1, max(0, deadline - time.perf_counter())))
            for s in ready:
                data, addr = s.recvfrom(2048)
                received = now_ns()
                if capture:
                    capture.write(json.dumps(dict(clock=CLOCK_NAME, received_ns=received, packet_hex=data.hex()))+'\n')
                try:
                    observation = matcher.feed(data, received)
                except ValueError:
                    observation = None
                msg = parse_ptp(data)
                if msg is None:
                    continue
                counts[msg['kind']] = counts.get(msg['kind'], 0) + 1
                if observation is not None:
                    observed = round(observation.master_at_send_ns) - observation.received_ns
                    pairs += 1
                    if pairs <= 3:
                        print(f"Sync/FollowUp from {addr[0]} clock={msg['clock']} domain={msg['domain']} observed_offset_ns={observed}", flush=True)
        print(f'PTP messages by type: {counts}; matched Sync/FollowUp pairs: {pairs}')
        print('Reachable timing traffic only; path delay and DAC alignment are not measured.')
        return 0 if pairs else 2
    finally:
        if capture:
            capture.close()
        for s in sockets: s.close()

if __name__ == '__main__':
    raise SystemExit(main())
