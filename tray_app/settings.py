import ipaddress
import json
from pathlib import Path
import subprocess
import winreg
import netifaces

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'runtime/tray-settings.json'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_NAME = 'Airplay2PC'


def interfaces():
    result = []
    for guid in netifaces.interfaces():
        try:
            addresses = netifaces.ifaddresses(guid).get(netifaces.AF_INET, [])
        except ValueError:
            continue  # adapter disappeared during enumeration
        for address in addresses:
            ip = ipaddress.ip_address(address['addr'])
            if not ip.is_loopback and not ip.is_link_local:
                result.append((guid, str(ip), ip.is_private))
    return result


def validate(settings):
    if not isinstance(settings, dict):
        raise ValueError('Settings must be an object')
    name = settings.get('name', 'PC AirPlay')
    interface = settings.get('interface', '')
    diagnostics = settings.get('diagnostics', False)
    delay = settings.get('output_delay_ms', 0)
    if not isinstance(name, str) or not name.strip() or len(name) > 63 or any(ord(ch) < 32 for ch in name):
        raise ValueError('Receiver name must contain 1–63 printable characters.')
    if not isinstance(interface, str) or len(interface) > 128:
        raise ValueError('Invalid network interface.')
    if type(diagnostics) is not bool:
        raise ValueError('Invalid diagnostics setting.')
    if type(delay) is not int or not 0 <= delay <= 2000:
        raise ValueError('Output delay must be a whole number from 0 to 2000 ms.')
    return dict(name=name.strip(), interface=interface, diagnostics=diagnostics, output_delay_ms=delay)


def load():
    if CONFIG.exists():
        return validate(json.loads(CONFIG.read_text(encoding='utf-8')))
    candidates = [guid for guid, _, private in interfaces() if private]
    return dict(name='PC AirPlay', interface=candidates[0] if len(candidates) == 1 else '', diagnostics=False, output_delay_ms=0)


def save(settings):
    settings = validate(settings)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix('.tmp')
    temporary.write_text(json.dumps(settings, indent=2), encoding='utf-8')
    temporary.replace(CONFIG)


def startup_command():
    return subprocess.list2cmdline([str(ROOT/'.venv/Scripts/pythonw.exe'),
                                   str(ROOT/'tray_app/app.py'), '--autostart'])


def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, RUN_NAME)[0] == startup_command()
    except FileNotFoundError:
        return False


def set_startup(enabled):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                current = winreg.QueryValueEx(key, RUN_NAME)[0]
                if current == startup_command():
                    winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass
