# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['main_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('data/*', 'data'),
        ('db/*', 'db'),
        ('printer/*', 'printer'),
        ('logs/*', 'logs'),
        ('exportados/*', 'exportados'),
        ('excel_printer.db', '.'),
        ('excel_printer_config.json', '.'),
        # icon eliminado para evitar error
    ],
    hiddenimports=[
        'tkinter',
        'pandas',
        'openpyxl',
        'reportlab',
        'fpdf',
        'yaml',
        'PIL',
        'utils',
        'config_dialog',
        'excel_processor',
        'printer',
        'herramientas',
        'db',
        'autoloader',
        'logger_bod1',
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
    console=False,  # True si quieres consola visible para debug
    # icon eliminado
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
