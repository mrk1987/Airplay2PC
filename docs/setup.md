# Setup and development

This private repository contains patches and tests, rather than a copy of the
unlicensed upstream source. The local upstream checkout remains separate and ignored.

```powershell
git clone https://github.com/openairplay/airplay2-receiver.git
git -C airplay2-receiver checkout 6c343d3679ddb561c61566985acaaf587d0a3bd3
git -C airplay2-receiver apply --check ../patches/windows-playback.patch
git -C airplay2-receiver apply ../patches/windows-playback.patch
uv venv --python 3.12 .venv-ap2
uv pip install --python .venv-ap2/Scripts/python.exe -r requirements-windows.txt
```

The existing machine has the required dependencies. Fresh Windows installations
may need C/C++ build tools for netifaces; a fresh-machine install has not been tested.
The patch contains the complete local audio repair set.
Do not apply it a second time to the current checkout.

## Offline checks

Run from the project root. These tests do not open audio hardware or use the network:

```powershell
.\.venv-ap2\Scripts\python.exe -m unittest discover -s tests -v
```

Keep the upstream checkout at `airplay2-receiver/`: the launcher and regression
tests resolve that path. Virtual environments also stay at their existing paths.

## Updating the patch

The patch targets the pinned commit above. After an intentional upstream edit,
regenerate it with `git -C airplay2-receiver diff --binary` and save the output
as `patches/windows-playback.patch` without changing its encoding or line endings.
Review the patch for private data, run the offline tests, and verify it applies
to a clean checkout of the pinned commit before committing a replacement.
