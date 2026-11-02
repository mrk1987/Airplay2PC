"""Native Windows lifecycle tests: temporary TCP server/process trees, no audio."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
from tray_app.windows import Job, InstanceLock, NamedEvent, CREATE_SUSPENDED, set_app_identity, APP_ID
from tray_app import settings, runner
from tray_app.controller import port_owner


class WindowsLifecycleTests(unittest.TestCase):
    def test_explicit_windows_taskbar_identity(self):
        import ctypes
        from ctypes import wintypes
        set_app_identity()
        shell = ctypes.WinDLL('shell32')
        get_identity = shell.GetCurrentProcessExplicitAppUserModelID
        get_identity.argtypes = [ctypes.POINTER(wintypes.LPWSTR)]
        get_identity.restype = ctypes.c_long
        value = wintypes.LPWSTR()
        self.assertEqual(get_identity(ctypes.byref(value)), 0)
        try:
            self.assertEqual(value.value, APP_ID)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(value,ctypes.c_void_p))

    def test_listener_detection_on_current_windows_build(self):
        import socket
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0))
            listener.listen()
            self.assertEqual(port_owner(listener.getsockname()[1]),os.getpid())

    def test_job_close_kills_descendants_without_killing_unrelated_process(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], creationflags=subprocess.CREATE_NO_WINDOW)
        job = Job()
        child = None
        try:
            script = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); time.sleep(60)'
            process = subprocess.Popen([sys.executable, '-c', script], creationflags=subprocess.CREATE_NO_WINDOW | CREATE_SUSPENDED)
            job.assign(process)
            psutil.Process(process.pid).resume()
            deadline = time.perf_counter()+5
            descendants = []
            while time.perf_counter() < deadline:
                descendants = psutil.Process(process.pid).children(recursive=True)
                if descendants:
                    child = descendants[-1]
                    break
                time.sleep(0.05)
            self.assertIsNotNone(child)
            job.close()
            process.wait(timeout=5)
            _, alive = psutil.wait_procs(descendants, timeout=5)
            self.assertFalse(alive)
            self.assertIsNone(unrelated.poll())
        finally:
            job.close()
            unrelated.kill()
            unrelated.wait(timeout=5)

    def test_job_assignment_failure_does_not_execute_suspended_child(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder)/'must-not-exist'
            process = subprocess.Popen([sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()'],
                       creationflags=subprocess.CREATE_NO_WINDOW | CREATE_SUSPENDED)
            try:
                job = Job()
                job.close()
                with self.assertRaises(OSError): job.assign(process)
            finally:
                process.kill(); process.wait(timeout=5)
            self.assertFalse(marker.exists())

    def test_named_mutex_detects_duplicate(self):
        import uuid
        name = 'Local\\Airplay2PC-test-'+uuid.uuid4().hex
        first, second = InstanceLock(name), InstanceLock(name)
        try:
            self.assertFalse(first.already_running)
            self.assertTrue(second.already_running)
        finally:
            first.close(); second.close()

    def test_runner_cooperatively_stops_tcp_server(self):
        import socketserver
        import uuid
        event_name = 'Local\\Airplay2PC-test-stop-'+uuid.uuid4().hex
        event = NamedEvent(event_name)
        original_argv = sys.argv[:]
        original_path = sys.path[:]
        timer = None

        def fake_receiver(*args, **kwargs):
            nonlocal timer
            with socketserver.TCPServer(('127.0.0.1', 0), socketserver.BaseRequestHandler) as server:
                timer = threading.Timer(0.2, event.signal)
                timer.start()
                server.serve_forever()
        try:
            started = time.perf_counter()
            with patch.dict(os.environ, {'AIRPLAY2PC_STOP_EVENT':event_name}), patch('runpy.run_path', side_effect=fake_receiver):
                runner.main()
            self.assertLess(time.perf_counter()-started, 3)
        finally:
            if timer: timer.join(timeout=3)
            event.close()
            sys.argv[:], sys.path[:] = original_argv, original_path


class TraySettingsTests(unittest.TestCase):
    def test_delay_bounds_and_legacy_default(self):
        base = dict(name='PC AirPlay', interface='{test}', diagnostics=False)
        self.assertEqual(settings.validate(base)['output_delay_ms'],0)
        for delay in (-1,2001,1.5,True):
            with self.assertRaises(ValueError):settings.validate(dict(base,output_delay_ms=delay))
        self.assertEqual(settings.validate(dict(base,output_delay_ms=2000))['output_delay_ms'],2000)

    def test_roundtrip_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, 'CONFIG', Path(folder)/'settings.json'):
            value = dict(name='PC AirPlay', interface='{test-guid}', diagnostics=True)
            settings.save(value)
            self.assertEqual(settings.load(), settings.validate(value))
            for bad in ('', '\nname', 'x'*64):
                with self.assertRaises(ValueError): settings.validate(dict(value, name=bad))
            self.assertEqual(settings.load(), settings.validate(value))

    def test_startup_off_does_not_delete_foreign_registration(self):
        with patch('winreg.CreateKey') as key, patch('winreg.QueryValueEx', return_value=('unrelated-command', 1)), patch('winreg.DeleteValue') as delete:
            settings.set_startup(False)
            delete.assert_not_called()


if __name__ == '__main__': unittest.main()
