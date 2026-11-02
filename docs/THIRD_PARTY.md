# Third-party code and assets

The MIT licence covers my original code and documentation in this repository.
It does not change the rights to third-party code, patch context or trademarks.

## Receiver

Airplay2PC uses [openairplay/airplay2-receiver](https://github.com/openairplay/airplay2-receiver),
pinned to `6c343d3679ddb561c61566985acaaf587d0a3bd3`.
That revision has no licence file. The receiver is downloaded separately during
setup and is not bundled in the installer. The patches contain changes to that
receiver, including upstream context; the MIT licence is not a licence grant
for that upstream material. A public GitHub repository does not by itself
grant permission to redistribute or relicense its code.

## Icons

The current logo and tray icon were supplied for Airplay2PC. Older commits
contain third-party AirPlay artwork, which is excluded from the MIT licence
and is no longer used by the app or installer.

AirPlay, Windows and Spotify are trademarks of their respective owners.
Airplay2PC is independent and is not affiliated with or endorsed by those companies.

## Installer dependencies

Setup downloads uv, a managed CPython runtime, the receiver and Python packages.
Those projects retain their own licences. Downloads of uv and the receiver are
checked against pinned SHA-256 hashes. The package requirements include hashes.

The Windows installer includes a CPython 3.12 x64 wheel for netifaces 0.11.0
so setup does not need a C compiler. Its MIT licence is included inside the
wheel and copied beside it as `netifaces-LICENSE.txt`.

uv is available under MIT or Apache-2.0; CPython uses the Python Software
Foundation licence. Their downloaded distributions include their notices.
Other Python package notices are installed under `.venv/Lib/site-packages/`.
