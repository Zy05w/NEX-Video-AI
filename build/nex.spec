# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "nex" / "resources" / "nex.ico"), "nex/resources"),
    (str(ROOT / "nex" / "resources" / "nex.png"), "nex/resources"),
    (str(ROOT / "nex" / "resources" / "arrow_down.png"), "nex/resources"),
    (str(ROOT / "nex" / "resources" / "arrow_up.png"), "nex/resources"),
]

hiddenimports = []

a = Analysis(
    [str(ROOT / "build" / "nex_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "pytest",
        "PyInstaller",
        "torch",
        "cv2",
        "numpy",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NEX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "nex" / "resources" / "nex.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="NEX",
)
