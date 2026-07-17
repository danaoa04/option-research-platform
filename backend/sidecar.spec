# PyInstaller definition for the fixed desktop backend executable.

from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    ["sidecar.py"],
    pathex=["."],
    binaries=[],
    datas=[
        (str(root / "backend/database/migrations"), "backend/database/migrations"),
        (str(root / "release"), "release"),
        (str(root / "LICENSE"), "."),
        (str(root / "docs/Third_Party_Notices.md"), "docs"),
    ],
    hiddenimports=["backend.main", "backend.database.provider_operations"],
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
