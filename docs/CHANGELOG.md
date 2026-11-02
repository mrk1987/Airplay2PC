# Changelog

## 0.1.1 - 2026-11-02

- Start the receiver automatically when opening the app.
- Open Settings when no LAN interface is selected, then start after saving.
- Migrate the old development shortcut and refresh its Airplay2PC logo.
- Group setup scripts and dependencies under `packaging/`, and supporting documents under `docs/`.
- Remove internal workspace and session notes from the public documentation.

## 0.1.0 - 2026-11-02

First public release.

- Windows AirPlay receiver with fixes for robotic playback, extra PCM padding,
  packet ordering and iPhone volume control.
- Tray controls for start, stop, restart, network interface and startup at login.
- Fixed output delay from 0 to 2000 ms.
- Per-user online installer, source package and SHA-256 checksums.
- Patched zeroconf dependency for network discovery.
- Fixed discovery shutdown to use zeroconf's synchronous unregister API.
- Airplay2PC logo, white tray icon and GitHub README banner.

Playback sounds clean and sync sounds right in my setup. I've tested with
Spotify set to lossless streaming. Precise multiroom alignment, long-run drift
and end-to-end lossless output remain unmeasured. The experimental timing
pipeline is not connected to audio scheduling.
