# Windows tray app

Airplay2PC runs in your Windows session. The tray icon controls the receiver,
and Settings has its own taskbar icon. There's no Windows service to install
and no administrator access required.

## Install and run

The [release installer](https://github.com/mrk1987/Airplay2PC/releases/latest)
handles setup and opens Settings. For a development checkout, first follow
[Setup](setup.md), then run:

```powershell
uv pip install --python .venv/Scripts/python.exe -r packaging/requirements-tray.txt
.\packaging\Install-Tray.ps1
.\packaging\Start-Tray.ps1
```

The installer creates a per-user Start menu shortcut with the Airplay2PC logo.
Launching the app starts the receiver automatically. If a LAN interface is
missing, Settings opens first; saving an interface starts the receiver.
Double-click the tray icon (or launch it again) to open Settings. Right-click for controls.
Settings preselects a private IPv4 interface only if there is exactly one candidate;
otherwise choose the physical LAN explicitly. Name, interface and diagnostics are
stored locally in ignored `runtime/tray-settings.json`.

## Controls and status

- **Start / Stop / Restart:** receiver lifecycle without a console window.
- **Stopped / Starting / Ready / Stopping / Failed:** shown as menu text and tooltip.
  Ready means the owned receiver socket is listening, not that audio is playing
  or multiroom synchronisation has been verified.
- **Settings:** receiver name, LAN interface, output delay, diagnostics and login startup.
  Changes apply at the next receiver start.
- **Output delay:** 0–2000 ms, in whole milliseconds; positive means later.
  A fixed PCM delay line preserves byte counts and playback speed. Zero is an
  exact pass-through. Restart to apply; pause/flush discards the retained tail
  so old audio is not replayed. The final delayed tail is discarded on Stop.
  Negative values are not offered: advancing playback requires controlled removal
  of existing buffering or shared-clock scheduling. This setting does not fix drift.
  The foreground launcher also accepts `-OutputDelayMs`.
- **Open logs:** opens `runtime/`; `receiver.log` is receiver output and `tray.log`
  is the rotating app log. These can contain private protocol/device metadata.
- **Timing diagnostics:** records numeric anchors after the next restart. It
  does not enable experimental synchronisation or record media.
- **Start at login:** opt-in, off for a fresh installation. Uses the current user's
  Run registry value, starting the tray and receiver with saved settings. Existing
  preferences are preserved. No firewall rules or elevated startup task is created.
- **Quit and stop receiver:** closes the app and its receiver process tree.

The tray is single-instance per workspace. Launching it again opens Settings.
It refuses to take over an independently running receiver or an occupied port.
Stop only affects the receiver it started.

## Process ownership

The receiver starts suspended and is assigned to a Windows Job Object before it
can spawn children. Closing that job kills its descendants even if the tray crashes.
Stop first signals a named event; the runner asks the RTSP server to shut down,
allowing mDNS withdrawal. After three seconds, the job closes to ensure cleanup.
The default audio implementation is not patched by the tray app.

Readiness uses a private event signalled by the owned server after checking
`SO_ACCEPTCONN`. This Windows build reports listening TCP sockets as `NONE` in
psutil, so generic TCP status alone is not used as readiness evidence.

## Checks and limitations

Run `.\packaging\Test-Airplay.ps1` after installing the tray requirements. Tests cover real
Job Object cleanup, suspended-start failure, unrelated-process isolation, duplicate
mutexes, cooperative shutdown and settings validation. Actual receiver Start,
Restart and Stop were also checked without sending audio.

The UI uses Windows native menus and ttk system controls, keyboard focus, text
status and labelled settings. I haven't completed an automated screenshot and
interaction test of the UI.

For an installed release, quit the tray and remove Airplay2PC through Windows'
installed-apps list. Pairings, settings and logs stay in `runtime/`.
For a development checkout, quit the tray, disable Start at login in Settings,
then remove its Start menu shortcut.

For troubleshooting, `pythonw.exe tray_app/app.py --no-autostart` opens the
tray without starting the receiver. Start at login remains opt-in.
