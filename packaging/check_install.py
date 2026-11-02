"""Import every native dependency without opening sockets or audio devices."""
import sys
from pathlib import Path
import tkinter
import av
import pyaudio
import netifaces
import zeroconf
import pystray
import psutil
from PIL import Image
from pycaw.pycaw import AudioUtilities

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'vendor/airplay2-receiver'))
from ap2.connections.audio import Audio

print('Python:', sys.version.split()[0])
print('Tcl:', tkinter.Tcl().eval('info patchlevel'))
print('zeroconf:', zeroconf.__version__)
print('Native dependencies and patched receiver imports OK')
