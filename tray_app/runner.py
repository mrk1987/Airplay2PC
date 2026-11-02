"""Receiver host with cooperative server shutdown. Child tree is owned by tray Job."""
from pathlib import Path
import os
import runpy
import socketserver
import socket
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from tray_app.windows import NamedEvent
    stop = NamedEvent(os.environ['AIRPLAY2PC_STOP_EVENT'], open_existing=True)
    ready = NamedEvent(os.environ['AIRPLAY2PC_READY_EVENT'], open_existing=True) if os.environ.get('AIRPLAY2PC_READY_EVENT') else None
    original = socketserver.BaseServer.serve_forever

    def serve(server, poll_interval=0.2):
        if ready and server.server_address[1] == 7000 and server.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN):
            ready.signal()  # only after this owned server actually listens
        finished = threading.Event()

        def watch():
            while not finished.is_set():
                if stop.wait(100):
                    server.shutdown()
                    return
        thread = threading.Thread(target=watch, daemon=True)
        thread.start()
        try:
            return original(server, poll_interval)
        finally:
            finished.set()
            if ready:
                ready.reset()

    socketserver.BaseServer.serve_forever = serve
    receiver = ROOT/'vendor/airplay2-receiver/ap2-receiver.py'
    sys.path.insert(0, str(receiver.parent))
    sys.argv[0] = str(receiver)
    try:
        runpy.run_path(str(receiver), run_name='__main__')
    finally:
        socketserver.BaseServer.serve_forever = original
        stop.close()
        if ready:
            ready.close()


if __name__ == '__main__':
    main()
