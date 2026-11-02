"""Set an unsigned Windows executable's icon using native resource APIs."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import struct


def replace_icon(executable, icon):
    data = Path(icon).read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', data)
    if reserved or kind != 1 or not 1 <= count <= 32:
        raise ValueError('Invalid ICO header')
    entries = []
    for index in range(count):
        values = struct.unpack_from('<BBBBHHII', data, 6 + index * 16)
        size, offset = values[-2:]
        image = data[offset:offset + size]
        if len(image) != size or not size:
            raise ValueError('Truncated ICO image')
        entries.append((values, image))

    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    api.LoadLibraryExW.restype = wintypes.HMODULE
    api.FreeLibrary.argtypes = [wintypes.HMODULE]
    api.FreeLibrary.restype = wintypes.BOOL
    name_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ssize_t)
    language_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_ssize_t)
    api.EnumResourceNamesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, name_callback, ctypes.c_ssize_t]
    api.EnumResourceNamesW.restype = wintypes.BOOL
    api.EnumResourceLanguagesW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, language_callback, ctypes.c_ssize_t]
    api.EnumResourceLanguagesW.restype = wintypes.BOOL
    groups = []

    @language_callback
    def language(module, resource_type, name, lang, context):
        groups.append((name if name < 65536 else ctypes.wstring_at(name), lang))
        return True

    @name_callback
    def resource(module, resource_type, name, context):
        api.EnumResourceLanguagesW(module, resource_type, name, language, 0)
        return True

    handle = api.LoadLibraryExW(str(Path(executable).resolve()), None, 2)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        api.EnumResourceNamesW(handle, 14, resource, 0)
    finally:
        api.FreeLibrary(handle)
    if not groups:
        groups = [(1, 0)]
    api.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    api.BeginUpdateResourceW.restype = wintypes.HANDLE
    api.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p, wintypes.DWORD]
    api.UpdateResourceW.restype = wintypes.BOOL
    api.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    api.EndUpdateResourceW.restype = wintypes.BOOL
    update = api.BeginUpdateResourceW(str(Path(executable).resolve()), False)
    if not update:
        raise ctypes.WinError(ctypes.get_last_error())
    committed = False
    try:
        group_data = struct.pack('<HHH', 0, 1, count)
        for index, (values, _) in enumerate(entries, 1):
            group_data += struct.pack('<BBBBHHIH', *values[:-1], index)
        for lang in {lang for _, lang in groups}:
            for index, (_, image) in enumerate(entries, 1):
                buffer = ctypes.create_string_buffer(image)
                if not api.UpdateResourceW(update, 3, index, lang, buffer, len(image)):
                    raise ctypes.WinError(ctypes.get_last_error())
        for name, lang in groups:
            pointer = name if isinstance(name, int) else ctypes.cast(ctypes.c_wchar_p(name), ctypes.c_void_p)
            buffer = ctypes.create_string_buffer(group_data)
            if not api.UpdateResourceW(update, 14, pointer, lang, buffer, len(group_data)):
                raise ctypes.WinError(ctypes.get_last_error())
        if not api.EndUpdateResourceW(update, False):
            raise ctypes.WinError(ctypes.get_last_error())
        committed = True
    finally:
        if not committed:
            api.EndUpdateResourceW(update, True)
    # Updating resources leaves the old PE checksum in place.
    imagehlp = ctypes.WinDLL('imagehlp', use_last_error=True)
    imagehlp.MapFileAndCheckSumW.argtypes = [wintypes.LPCWSTR,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
    imagehlp.MapFileAndCheckSumW.restype = wintypes.DWORD
    previous, computed = wintypes.DWORD(), wintypes.DWORD()
    if imagehlp.MapFileAndCheckSumW(str(Path(executable).resolve()), ctypes.byref(previous), ctypes.byref(computed)):
        raise OSError('Cannot calculate installer PE checksum')
    with Path(executable).open('r+b') as output:
        output.seek(0x3c)
        pe_offset = struct.unpack('<I', output.read(4))[0]
        output.seek(pe_offset)
        if output.read(4) != b'PE\0\0':
            raise ValueError('Invalid Windows executable')
        output.seek(pe_offset + 24 + 64)
        output.write(struct.pack('<I', computed.value))
