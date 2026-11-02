"""Receiver lifecycle, deliberately separate from UI callbacks and audio processing."""
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
import psutil
from .settings import ROOT, validate
from .windows import Job, NamedEvent, CREATE_SUSPENDED


def port_owner(port=7000):
    for connection in psutil.net_connections(kind='tcp'):
        if (connection.laddr.port == port and not connection.raddr
                and connection.status in (psutil.CONN_LISTEN, psutil.CONN_NONE)):
            return connection.pid
    return None


class Controller:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.process = self.job = self.stop_event = self.ready_event = self.log = None
        self.state = 'Stopped'
        self.error = ''
        self._lock = threading.RLock()

    def snapshot(self):
        with self._lock:
            self._poll()
            return self.state, self.error

    def _release(self):
        if self.job:
            self.job.close()  # kills even descendants surviving root-process exit
        if self.stop_event:
            self.stop_event.close()
        if self.ready_event:
            self.ready_event.close()
        if self.log:
            self.log.close()
        self.process = self.job = self.stop_event = self.ready_event = self.log = None

    def _poll(self):
        if self.process and self.process.poll() is not None:
            code = self.process.returncode
            self._release()
            self.state, self.error = 'Failed', f'Receiver exited ({code}). Open receiver.log for details.'
        elif self.process and self.state == 'Ready' and not self.ready_event.wait(0):
            self._release()
            self.state, self.error = 'Failed', 'Receiver stopped listening. Open receiver.log for details.'

    def start(self, settings):
        with self._lock:
            self._poll()
            if self.process:
                self.state = 'Ready'
                return
            settings = validate(settings)
            if not settings['interface']:
                raise ValueError('Choose a LAN interface in Settings first.')
            if port_owner() is not None:
                raise RuntimeError('Port 7000 is already in use. Stop the other receiver first; it will not be taken over.')
            # Also catch another copy while it is starting, before it binds its port.
            receiver = str((self.root/'vendor/airplay2-receiver/ap2-receiver.py').resolve()).lower()
            runner = str((self.root/'tray_app/runner.py').resolve()).lower()
            for proc in psutil.process_iter(['cmdline']):
                args = proc.info['cmdline'] or []
                if any(str(arg).replace('/', '\\').lower() in (receiver.replace('/', '\\'), runner.replace('/', '\\')) for arg in args):
                    raise RuntimeError('A receiver for this workspace is already running outside this tray app.')
            runtime = self.root/'runtime'
            (runtime/'pairings').mkdir(parents=True, exist_ok=True)
            self.state, self.error = 'Starting', ''
            try:
                self.job = Job()
                event_name = 'Local\\Airplay2PC-stop-'+uuid.uuid4().hex
                self.stop_event = NamedEvent(event_name)
                self.ready_event = NamedEvent(event_name+'-ready')
                self.log = (runtime/'receiver.log').open('ab', buffering=0)
                env = os.environ.copy()
                env['AIRPLAY2PC_STOP_EVENT'] = event_name
                env['AIRPLAY2PC_READY_EVENT'] = event_name+'-ready'
                env['PYTHONPATH'] = str(self.root)
                env.pop('AIRPLAY_TIMING_LOG_DIR', None)
                if settings['diagnostics']:
                    env['AIRPLAY_TIMING_LOG_DIR'] = str(runtime/'timing')
                args = [str(self.root/'.venv/Scripts/python.exe'), '-u', str(self.root/'tray_app/runner.py'),
                        '-m', settings['name'], '-n', settings['interface'], '-ftor', '61']
                self.process = subprocess.Popen(args, cwd=runtime, env=env, stdin=subprocess.DEVNULL,
                          stdout=self.log, stderr=subprocess.STDOUT,
                          creationflags=subprocess.CREATE_NO_WINDOW | CREATE_SUSPENDED)
                self.job.assign(self.process)  # before any Python or child code can run
                psutil.Process(self.process.pid).resume()
                deadline = time.perf_counter()+15
                while time.perf_counter() < deadline:
                    self._poll()
                    if not self.process:
                        raise RuntimeError(self.error)
                    if self.ready_event.wait(0):
                        self.state = 'Ready'
                        return
                    time.sleep(0.1)
                raise RuntimeError('Receiver did not become ready within 15 seconds. Open receiver.log.')
            except Exception as exc:
                failed_process = self.process
                # If job assignment failed, process may not belong to job yet.
                if self.process and self.process.poll() is None:
                    self.process.kill()
                self._release()
                if failed_process:
                    failed_process.wait(timeout=5)
                self.state, self.error = 'Failed', str(exc)
                raise

    def stop(self):
        with self._lock:
            self.state = 'Stopping'
            try:
                if self.process and self.process.poll() is None:
                    self.stop_event.signal()
                    try:
                        self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                process = self.process
                self._release()
                if process:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.state, self.error = 'Failed', 'Receiver cleanup timed out.'
                        raise RuntimeError(self.error)
                self.state, self.error = 'Stopped', ''

    def restart(self, settings):
        self.stop()
        self.start(settings)
