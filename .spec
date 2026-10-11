from PyInstaller.building.build_main import Analysis  # type: ignore
from PyInstaller.building.api import PYZ, EXE, COLLECT  # type: ignore


a = Analysis(
    ["src/fast_math/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[("assets/", "assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)


pyz = PYZ(a.pure)


exe = EXE(
    pyz,
    a.scripts,
    [
        ("X utf8=1", None, "OPTION"),
    ],
    exclude_binaries=True,
    name="FASTMATH",
    icon="assets/icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FASTMATH",
)
