# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for DeveloperOS.exe (desktop ladder step C, D-0031).

Build (from the packaging/ directory; PyInstaller is a DEV-TIME dependency only —
the runtime stays stdlib-only):

    pip install pyinstaller
    pyinstaller --noconfirm --clean devos.spec

Output: dist/DeveloperOS.exe — a single file that runs the `devos app` launcher
(D-0030): starts/reuses the local dashboard and opens the browser. Console stays
visible on purpose for now: it is the server log and the Ctrl+C handle.
"""
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["launch_devos.py"],
    pathex=[".."],
    binaries=[],
    datas=[
        # Runtime data files: the vendored dashboard and the SQLite schema.
        ("../devos/api/static", "devos/api/static"),
        ("../devos/storage/schema.sql", "devos/storage"),
    ],
    # The CLI registers commands via import side effects; collect everything
    # under devos so optional/lazy imports are never missed.
    hiddenimports=collect_submodules("devos"),
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DeveloperOS",
    icon="devos.ico",
    console=True,           # server log + Ctrl+C; windowless is a later refinement
    upx=False,              # avoid AV false positives from packed executables
    strip=False,
    bootloader_ignore_signals=False,
    disable_windowed_traceback=False,
)
