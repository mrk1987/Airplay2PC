"""Windows handles own process trees. No PID files or unrelated process kills."""
import ctypes as c
from ctypes import wintypes as w

k32 = c.WinDLL('kernel32', use_last_error=True)
k32.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
k32.CreateJobObjectW.restype = w.HANDLE
k32.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
k32.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
k32.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
k32.CloseHandle.argtypes = [w.HANDLE]
k32.CreateMutexW.argtypes = [c.c_void_p, w.BOOL, w.LPCWSTR]
k32.CreateMutexW.restype = w.HANDLE
k32.CreateEventW.argtypes = [c.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR]
k32.CreateEventW.restype = w.HANDLE
k32.OpenEventW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
k32.OpenEventW.restype = w.HANDLE
k32.SetEvent.argtypes = [w.HANDLE]
k32.ResetEvent.argtypes = [w.HANDLE]
k32.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
CREATE_SUSPENDED = 0x00000004
APP_ID = 'mrk1987.Airplay2PC'


def set_app_identity():
    # Prevent Windows bitmap-scaling the settings window and taskbar icon on HiDPI displays.
    user = c.WinDLL('user32', use_last_error=True)
    user.SetProcessDpiAwarenessContext.argtypes = [c.c_void_p]
    user.SetProcessDpiAwarenessContext(c.c_void_p(-4))  # PER_MONITOR_AWARE_V2
    shell = c.WinDLL('shell32', use_last_error=True)
    shell.SetCurrentProcessExplicitAppUserModelID.argtypes = [w.LPCWSTR]
    shell.SetCurrentProcessExplicitAppUserModelID.restype = c.c_long
    result = shell.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    if result < 0:
        raise OSError(f'Cannot set Windows app identity: HRESULT {result:#x}')


class BasicLimits(c.Structure):
    _fields_ = [('per_process', c.c_int64), ('per_job', c.c_int64), ('flags', w.DWORD),
                ('minimum_working_set', c.c_size_t), ('maximum_working_set', c.c_size_t),
                ('active_processes', w.DWORD), ('affinity', c.c_size_t),
                ('priority', w.DWORD), ('scheduling', w.DWORD)]


class IoCounters(c.Structure):
    _fields_ = [(name, c.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]


class ExtendedLimits(c.Structure):
    _fields_ = [('basic', BasicLimits), ('io', IoCounters), ('process_memory', c.c_size_t),
                ('job_memory', c.c_size_t), ('peak_process_memory', c.c_size_t), ('peak_job_memory', c.c_size_t)]


def checked(result):
    if not result:
        raise c.WinError(c.get_last_error())
    return result


class Job:
    def __init__(self):
        self.handle = checked(k32.CreateJobObjectW(None, None))
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        try:
            checked(k32.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)))
        except Exception:
            self.close()
            raise

    def assign(self, process):
        checked(k32.AssignProcessToJobObject(self.handle, int(process._handle)))

    def close(self):
        if self.handle:
            checked(k32.CloseHandle(self.handle))
            self.handle = None


class NamedEvent:
    def __init__(self, name, *, open_existing=False):
        self.handle = checked(k32.OpenEventW(0x100002, False, name) if open_existing
                              else k32.CreateEventW(None, True, False, name))

    def signal(self):
        checked(k32.SetEvent(self.handle))

    def reset(self):
        checked(k32.ResetEvent(self.handle))

    def wait(self, milliseconds):
        result = k32.WaitForSingleObject(self.handle, milliseconds)
        if result not in (0, 258):
            raise c.WinError(c.get_last_error())
        return result == 0

    def close(self):
        if self.handle:
            k32.CloseHandle(self.handle)
            self.handle = None


class InstanceLock:
    def __init__(self, name):
        self.handle = checked(k32.CreateMutexW(None, False, name))
        self.already_running = c.get_last_error() == 183

    def close(self):
        if self.handle:
            k32.CloseHandle(self.handle)
            self.handle = None
