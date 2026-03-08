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
        # Google auth
        "google.auth",
        "google.auth.transport",
        "google.auth.transport.requests",
        "google.auth.exceptions",
        "google.oauth2",
        "google.oauth2.credentials",
        "google_auth_oauthlib",
        "google_auth_oauthlib.flow",
        # Google API client
        "googleapiclient",
        "googleapiclient.discovery",
        "googleapiclient.errors",
        "googleapiclient.http",
        # tkinter
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "_tkinter",
        # itselectric package
        "itselectric",
        "itselectric.auth",
        "itselectric.gmail",
        "itselectric.extract",
        "itselectric.sheets",
        "itselectric.cli",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pkg_resources.py2_warn",    # removed in modern setuptools
        "pycparser.lextab",          # generated file, not always present
        "pycparser.yacctab",         # generated file, not always present
        "charset_normalizer.md__mypyc",  # optional compiled extension
        "grpc",                          # not used by this app
        "google.api_core.operations_v1", # requires grpc, not used here
    ],
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
    info_plist={
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
    },
)
