# exelcior_apolo.spec — build one-folder con icono y archivo de versión
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# archivo de versión incrustado en el ejecutable
VERSION_FILE = "assets/version/exelcior_apolo_version.txt"

# icono del ejecutable (primer candidato existente)
ICON_FILE = None
for icon_candidate in [
    "data/image.ico",
    "app/data/image.ico",
    "assets/icon.ico",
]:
    if Path(icon_candidate).exists():
        ICON_FILE = icon_candidate
        break

# módulos que PyInstaller debe rastrear aunque se carguen dinámicamente
hiddenimports = [
    "sqlalchemy",
    *collect_submodules("tkinter"),
    *collect_submodules("sqlalchemy"),
    *collect_submodules("pandas"),
    *collect_submodules("openpyxl"),
    *collect_submodules("reportlab"),
    *collect_submodules("PIL"),
    "yaml",
    # si en algún entorno necesitas COM/Excel:
    # *collect_submodules("win32com"),
]

block_cipher = None

# Datos (carpetas/archivos) que deben ir junto al ejecutable.
# Solo añadimos si existen para que no moleste en CI.
datas = []
for entry in [
    "data",              # recursos en raíz (image.ico, db, etc.)
    "app/config",
    "app/core",
    "app/db",
    "app/gui",
    "app/logs",          # la app igual crea /logs si no existe
    "app/printer",
    "app/services",
    "app/utils",
    "app/data",          # ← logo, plantillas, etc. ¡IMPORTANTE!
    "assets",            # versión y otros recursos
]:
    p = Path(entry)
    if p.exists():
        datas.append((str(p), str(p)))

a = Analysis(
    ['app/main_app.py'],     # ← punto de entrada de tu app (ajústalo si usas otro)
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # limpia un poco el tamaño
        "tests", "test", "pytest", "nose",
    ],
    noarchive=False,   # deja .pyc comprimidos en base_library.zip (óptimo)
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
    console=False,              # GUI (Tkinter)
    version=VERSION_FILE,       # incrusta info de versión del exe
    icon=ICON_FILE,             # icono del ejecutable
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ExelciorApolo'
)
