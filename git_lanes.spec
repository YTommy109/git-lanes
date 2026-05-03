# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller ビルド設定。"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "backend" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "backend" / "templates"), "backend/templates"),
        (str(ROOT / "static"), "static"),
    ],
    hiddenimports=[
        "backend",
        "backend.main",
        "backend.db",
        "backend.models",
        "backend.paths",
        "backend.validation",
        "backend.routers",
        "backend.routers.api",
        "backend.routers.html",
        "backend.services",
        "backend.repositories",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "webview.platforms.cocoa",
        "_cffi_backend",
        "cffi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Git Lanes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Git Lanes",
)

app = BUNDLE(
    coll,
    name="Git Lanes.app",
    icon=str(ROOT / "resources" / "git-lanes.icns"),
    bundle_identifier="com.degino.git-lanes",
    info_plist={
        "CFBundleShortVersionString": "0.4.5",
        "NSHighResolutionCapable": True,
    },
)
