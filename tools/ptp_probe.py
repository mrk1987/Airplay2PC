"""Passive AirPlay/PTPv2 reachability probe; never adjusts the system clock.

Run while an iPhone is playing to an existing AirPlay 2 group. Offsets are
path-biased observations, NOT synchronisation accuracy measurements.
"""
import argparse
import select
import socket
import struct
import time


def parse_ptp(data):
    if len(data) < 34 or data[1] & 15 != 2:
        return None
    length = int.from_bytes(data[2:4], 'big')
    if length < 34 or length > len(data):
        return None
    result = dict(kind=data[0] & 15, domain=data[4], clock=data[20:28].hex(),
                  source=data[20:30].hex(), seq=int.from_bytes(data[30:32], 'big'))
    if result['kind'] in (0, 8) and length >= 44:
        result['origin_ns'] = int.from_bytes(data[34:40], 'big') * 10**9 + int.from_bytes(data[40:44], 'big')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface', required=True, help='Local LAN IPv4 address')
    parser.add_argument('--seconds', type=float, default=20)
    args = parser.parse_args()
    sockets = []
    counts = {}
    pending = {}
    pairs = 0
    try:
        for port in (319, 320):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sockets.append(s)
            # Exclusive bind: do not steal packets from another timing service.
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            s.bind(('', port))
            membership = socket.inet_aton('224.0.1.129') + socket.inet_aton(args.interface)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            ready, _, _ = select.select(sockets, [], [], min(1, max(0, deadline - time.monotonic())))
            for s in ready:
                data, addr = s.recvfrom(2048)
                received = time.monotonic_ns()
                msg = parse_ptp(data)
                if msg is None:
                    continue
                key = (msg['source'], msg['seq'], msg['domain'])
                counts[msg['kind']] = counts.get(msg['kind'], 0) + 1
                if msg['kind'] == 0:
                    pending[key] = received
                    if len(pending) > 256:
                        pending.pop(next(iter(pending)))
                elif msg['kind'] == 8 and key in pending and 'origin_ns' in msg:
                    observed = msg['origin_ns'] - pending.pop(key)
                    pairs += 1
                    if pairs <= 3:
                        print(f"Sync/FollowUp from {addr[0]} clock={msg['clock']} domain={msg['domain']} observed_offset_ns={observed}", flush=True)
        print(f'PTP messages by type: {counts}; matched Sync/FollowUp pairs: {pairs}')
        print('Reachable timing traffic only; path delay and DAC alignment are not measured.')
        return 0 if pairs else 2
    finally:
        for s in sockets: s.close()

if __name__ == '__main__':
    raise SystemExit(main())
