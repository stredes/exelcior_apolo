# exelcior_apolo.spec - empaquetado one-folder sin icono, con versión
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

VERSION_FILE = "assets/version/exelcior_apolo_version.txt"

hidden = [
    *collect_submodules("tkinter"),
    *collect_submodules("pandas"),
    *collect_submodules("openpyxl"),
    *collect_submodules("reportlab"),
    *collect_submodules("PIL"),
    "yaml",
]

block_cipher = None

# Solo incluimos las carpetas que realmente existen en tu repo
datas = []
for folder in [
    "app/config",
    "app/core",
    "app/db",
    "app/gui",
    "app/logs",
    "app/printer",
    "app/services",
    "app/utils",
    "assets"
]:
    if Path(folder).exists():
        datas.append((folder, folder))

a = Analysis(
    ['run_app.py'],   # <<--- entrada principal
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ExelciorApolo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # GUI (Tkinter)
    version=VERSION_FILE,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='ExelciorApolo'
)
