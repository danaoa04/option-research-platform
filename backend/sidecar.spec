# PyInstaller definition for the fixed desktop backend executable.

a = Analysis(
    ["sidecar.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=["backend.main"],
    hookspath=[],
    hooksconfig={},
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
    name="orp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
