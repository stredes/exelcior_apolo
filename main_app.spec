# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['app/main_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('app/config', 'app/config'),
        ('app/db', 'app/db'),
        ('app/printer', 'app/printer'),
        ('app/gui', 'app/gui'),
        ('logs', 'logs'),
        ('exportados', 'exportados'),
        ('etiqueta pedido.xlsx', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'pandas',
        'openpyxl',
        'reportlab',
        'fpdf',
        'yaml',
        'PIL',
        'app.utils.utils',
        'app.utils.logger_setup',
        'app.utils.logger_viewer',
        'app.config.config_dialog',
        'app.core.excel_processor',
        'app.core.herramientas',
        'app.core.autoloader',
        'app.core.logger_bod1',
        'app.db.database',
        'app.db.models'
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='excelcior_apolo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Cambia a True si quieres ver la terminal
    icon='icono_apolo.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='excelcior_apolo'
)
