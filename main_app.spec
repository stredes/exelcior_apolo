# main_app.spec
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
        ('etiqueta pedido.xlsx', '.'),  # Si quieres incluir una plantilla
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
        'app.db.models',
        'app.printer.printer',
        'app.printer.printer_linux',
        'app.gui.etiqueta_editor'
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
    console=True,  # Puedes poner False si quieres ocultar la consola en Windows
    icon='assets/icono.ico',
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
