"""Windows tray UI. Native menus and ttk settings; receiver work stays off UI thread."""
from pathlib import Path
import argparse
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageTk
import pystray
from tray_app import settings
from tray_app.controller import Controller
from tray_app.windows import InstanceLock, NamedEvent, set_app_identity


class App:
    def __init__(self, *, show_settings=False, autostart=True, events=None):
        set_app_identity()  # before Tk creates any HWNDs: separate taskbar identity from Python
        self.events = events or {}
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title('Airplay2PC')
        with Image.open(ROOT/'assets/icons/Airplay2PC-logo.png') as source:
            self.window_icons = [ImageTk.PhotoImage(source.resize((size,size),Image.Resampling.LANCZOS), master=self.root)
                                 for size in (256,128,64,48,32,24,16)]
        self.root.iconphoto(True, *self.window_icons)
        self.actions = queue.Queue()
        self.controller = Controller()
        self.busy = False
        self.pending_action = None
        self.quitting = False
        self.dialog = None
        try:
            self.config = settings.load()
        except (ValueError, OSError) as exc:
            logging.exception('Cannot load tray settings')
            self.config = dict(name='PC AirPlay', interface='', diagnostics=False, output_delay_ms=0)
            self.root.after(300, lambda error=str(exc): messagebox.showerror('Airplay2PC settings', error, parent=self.root))
        self.icon = pystray.Icon('Airplay2PC', Image.open(ROOT/'assets/icons/Airplay2PC-icon.png'),
                                'Airplay2PC — Stopped', self.menu())
        threading.Thread(target=self.icon.run, daemon=True).start()
        self.root.after(200, self.tick)
        self.schedule_startup(show_settings=show_settings, autostart=autostart)

    def schedule_startup(self, *, show_settings, autostart):
        self.start_when_configured = autostart and not self.config['interface']
        if show_settings or self.start_when_configured:
            self.root.after(300, self.settings_dialog)
        if autostart and self.config['interface']:
            self.root.after(400, lambda: self.run_operation('start'))

    def start_after_settings(self):
        if self.start_when_configured and self.config['interface']:
            self.start_when_configured = False
            self.run_operation('start')

    def enqueue(self, action):
        return lambda *_: self.actions.put(action)

    def menu(self):
        item = pystray.MenuItem
        return pystray.Menu(
            item(lambda _: 'Status: '+self.controller.state, None, enabled=False),
            item('Start', self.enqueue('start'), enabled=lambda _: not self.busy and self.controller.state in ('Stopped','Failed')),
            item('Stop', self.enqueue('stop'), enabled=lambda _: not self.busy and self.controller.state in ('Ready','Failed')),
            item('Restart', self.enqueue('restart'), enabled=lambda _: not self.busy and self.controller.state == 'Ready'),
            pystray.Menu.SEPARATOR,
            item('Settings…', self.enqueue('settings'), default=True, enabled=lambda _: not self.busy),
            item('Open logs', self.enqueue('logs')),
            item('Timing diagnostics', self.enqueue('diagnostics'), checked=lambda _: self.config['diagnostics'], enabled=lambda _: not self.busy),
            item('Start at login', self.enqueue('startup'), checked=lambda _: settings.startup_enabled(), enabled=lambda _: not self.busy),
            pystray.Menu.SEPARATOR,
            item('Quit and stop receiver', self.enqueue('quit'), enabled=lambda _: not self.busy))

    def run_operation(self, action):
        if self.busy:
            if self.pending_action != 'quit':
                self.pending_action = action  # latest request wins; Quit cannot be displaced
            return
        self.busy = True
        self.controller.state = 'Stopping' if action in ('stop','quit') else 'Starting'
        self.icon.update_menu()

        def work():
            try:
                if action in ('stop','quit'):
                    self.controller.stop()
                else:
                    getattr(self.controller, action)(dict(self.config))
                self.actions.put(('complete', action, None))
            except Exception as exc:
                logging.exception('Receiver operation %s failed', action)
                self.controller.state, self.controller.error = 'Failed', str(exc)
                self.actions.put(('complete', action, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def tick(self):
        for action, event in self.events.items():
            if event.wait(0):
                event.reset()
                self.actions.put(action)
        try:
            while True:
                action = self.actions.get_nowait()
                if isinstance(action, tuple):
                    _, operation, error = action
                    self.busy = False
                    if error:
                        messagebox.showerror('Airplay2PC', error, parent=self.dialog or self.root)
                    if operation == 'quit' and not error:
                        self.icon.stop()
                        self.root.destroy()
                        return
                    if self.pending_action:
                        pending, self.pending_action = self.pending_action, None
                        self.actions.put(pending)
                elif action in ('start','stop','restart','quit'):
                    self.run_operation(action)
                elif action == 'settings':
                    self.settings_dialog()
                elif action == 'logs':
                    os.startfile(ROOT/'runtime')
                elif action in ('diagnostics','startup'):
                    try:
                        if action == 'startup':
                            settings.set_startup(not settings.startup_enabled())
                        else:
                            updated = dict(self.config, diagnostics=not self.config['diagnostics'])
                            settings.save(updated)
                            self.config = updated
                            if self.controller.state == 'Ready':
                                self.icon.notify('Timing diagnostics will change after Restart.', 'Airplay2PC')
                    except (ValueError, OSError) as exc:
                        messagebox.showerror('Airplay2PC', str(exc), parent=self.root)
                self.icon.update_menu()
        except queue.Empty:
            pass
        if not self.busy:
            previous = self.controller.state
            state, error = self.controller.snapshot()
            if state == 'Failed' and previous != 'Failed':
                self.icon.notify(error, 'Airplay2PC receiver stopped')
        self.icon.title = ('Airplay2PC — '+self.controller.state)[:127]
        # Status is text, never just an icon colour. Ready means listener, not synced playback.
        status = dict(state=self.controller.state, error=self.controller.error,
                      receiver_pid=self.controller.process.pid if self.controller.process else None,
                      tray_pid=os.getpid(), busy=self.busy)
        try:
            path = ROOT/'runtime/tray-status.json'
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(status), encoding='utf-8')
            temporary.replace(path)
        except PermissionError:
            pass  # a reader may briefly hold the replace target on Windows
        except OSError:
            logging.exception('Cannot write tray status')
        self.root.after(400, self.tick)

    def settings_dialog(self):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        dialog = self.dialog = tk.Toplevel(self.root)
        dialog.title('Airplay2PC settings')
        dialog.iconphoto(False, *self.window_icons)
        dialog.resizable(False, False)
        dialog.columnconfigure(0, weight=1)
        frame = ttk.Frame(dialog, padding=20)
        frame.grid(sticky='nsew')
        frame.columnconfigure(0, weight=1)
        name = tk.StringVar(value=self.config['name'])
        selected = tk.StringVar()
        diagnostics = tk.BooleanVar(value=self.config['diagnostics'])
        delay = tk.StringVar(value=str(self.config['output_delay_ms']))
        startup = tk.BooleanVar(value=settings.startup_enabled())
        ttk.Label(frame, text='Receiver name').grid(row=0, column=0, sticky='w')
        entry = ttk.Entry(frame, textvariable=name, width=52)
        entry.grid(row=1, column=0, sticky='ew', pady=(4,16))
        ttk.Label(frame, text='LAN interface').grid(row=2, column=0, sticky='w')
        try:
            available = settings.interfaces()
        except OSError:
            available = []
        choices = {f'{ip}  —  {guid}': guid for guid, ip, _ in available}
        for label, guid in choices.items():
            if guid == self.config['interface']:
                selected.set(label)
                break
        combo = ttk.Combobox(frame, textvariable=selected, values=list(choices), state='readonly', width=65)
        combo.grid(row=3, column=0, sticky='ew', pady=(4,6))
        ttk.Label(frame, text='Choose your home LAN. Avoid VPN and virtual adapters.', wraplength=460).grid(row=4, column=0, sticky='w', pady=(0,16))
        ttk.Label(frame, text='Output delay (ms)').grid(row=5, column=0, sticky='w')
        ttk.Spinbox(frame, from_=0, to=2000, increment=10, textvariable=delay, width=10).grid(row=6, column=0, sticky='w', pady=(4,6))
        ttk.Label(frame, text='0–2000 ms. Higher values play later. 0 adds no delay.', wraplength=460).grid(row=7, column=0, sticky='w', pady=(0,16))
        ttk.Checkbutton(frame, text='Record timing diagnostics', variable=diagnostics).grid(row=8, column=0, sticky='w')
        ttk.Checkbutton(frame, text='Start receiver at Windows login', variable=startup).grid(row=9, column=0, sticky='w', pady=(8,16))
        ttk.Label(frame, text='Changes apply the next time the receiver starts.\nA fixed delay does not correct clock drift.', wraplength=460).grid(row=10, column=0, sticky='w', pady=(0,18))
        buttons = ttk.Frame(frame)
        buttons.grid(row=11, column=0, sticky='e')

        def apply():
            try:
                if selected.get() not in choices:
                    raise ValueError('Choose an available LAN interface.')
                updated = settings.validate(dict(name=name.get(), interface=choices[selected.get()], diagnostics=diagnostics.get(), output_delay_ms=int(delay.get())))
                settings.set_startup(startup.get())
                settings.save(updated)
                self.config = updated
            except (ValueError, OSError) as exc:
                messagebox.showerror('Airplay2PC settings', str(exc), parent=dialog)
                return
            dialog.destroy()
            self.dialog = None
            self.icon.update_menu()
            self.start_after_settings()
        ttk.Button(buttons, text='Cancel', command=dialog.destroy).pack(side='left', padx=(0,8))
        ttk.Button(buttons, text='Save', command=apply).pack(side='left')
        dialog.bind('<Return>', lambda _: apply())
        dialog.bind('<Escape>', lambda _: dialog.destroy())
        entry.focus_set()
        dialog.update_idletasks()
        width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        dialog.geometry(f'+{max(0,(dialog.winfo_screenwidth()-width)//2)}+{max(0,(dialog.winfo_screenheight()-height)//2)}')
        dialog.lift()

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.controller.stop()
            self.icon.stop()
            try:
                (ROOT/'runtime/tray-status.json').write_text(json.dumps(dict(
                    state='Stopped', error='', receiver_pid=None, tray_pid=None, busy=False)), encoding='utf-8')
            except OSError:
                pass


def parse_launch_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings', action='store_true')
    parser.add_argument('--autostart', action='store_true', default=True)
    parser.add_argument('--no-autostart', action='store_false', dest='autostart',
                        help='Open the tray without starting the receiver')
    parser.add_argument('--action', choices=('start','stop','restart','quit','settings'))
    return parser.parse_args(argv)


def main():
    args = parse_launch_args()
    runtime = ROOT/'runtime'
    runtime.mkdir(exist_ok=True)
    handler = RotatingFileHandler(runtime/'tray.log', maxBytes=1_000_000, backupCount=2, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')
    identity = hashlib.sha256(str(ROOT).lower().encode()).hexdigest()[:16]
    prefix = 'Local\\Airplay2PC-tray-'+identity
    mutex = InstanceLock(prefix)
    if mutex.already_running:
        try:
            event = NamedEvent(prefix+'-'+(args.action or 'settings'), open_existing=True)
            event.signal()
            event.close()
        finally:
            mutex.close()
        return
    if args.action:
        mutex.close()
        return  # action-only invocation never starts a new receiver or tray
    events = {action: NamedEvent(prefix+'-'+action) for action in ('start','stop','restart','quit','settings')}
    try:
        App(show_settings=args.settings, autostart=args.autostart, events=events).run()
    except Exception:
        logging.exception('Tray application failed')
        raise
    finally:
        for event in events.values():
            event.close()
        mutex.close()


if __name__ == '__main__':
    main()
