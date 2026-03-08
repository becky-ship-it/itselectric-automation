# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Email → Sheets macOS app.
# Build with: pyinstaller app.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ["src/itselectric/gui.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        *collect_data_files("customtkinter"),
        *collect_data_files("certifi"),
    ],
    hiddenimports=[
        *collect_submodules("google"),
        *collect_submodules("googleapiclient"),
        "itselectric",
        "itselectric.auth",
        "itselectric.gmail",
        "itselectric.extract",
        "itselectric.sheets",
        "itselectric.cli",
        "pkg_resources.py2_warn",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="it's electric automation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="it's electric automation",
)

app = BUNDLE(
    coll,
    name="it's electric automation.app",
    icon=None,
    bundle_identifier="com.itselectric.automation",
)
