# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

project_root = Path(__file__).resolve().parent
app_dir = project_root / "exelcior_apolo-main" / "app"

a = Analysis(
    [str(app_dir / "main_app.py")],
    pathex=[str(app_dir)],
    binaries=[],
    datas=[
        (str(app_dir / 'data'), 'data'),
        (str(app_dir / 'db'), 'db'),
        (str(app_dir / 'printer'), 'printer'),
        (str(app_dir / 'logs'), 'logs'),
        (str(app_dir / 'exportados'), 'exportados'),
        (str(app_dir / 'excel_printer.db'), '.'),
        (str(app_dir / 'excel_printer_config.json'), '.'),
    ],
    hiddenimports=[
        'tkinter',
        'pandas',
        'openpyxl',
        'reportlab',
        'fpdf',
        'yaml',
        'PIL',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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
    console=False,
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
