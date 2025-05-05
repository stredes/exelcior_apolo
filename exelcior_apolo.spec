# -*- mode: python ; coding: utf-8 -*-
import sys  # 👈 NECESARIO para usar sys.platform
block_cipher = None

a = Analysis(
    ['app/main_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[ 
        # Directorios a incluir
        ('app/db', 'app/db'),
        ('app/data', 'app/data'),
        ('app/printer', 'app/printer'),
        ('app/logs', 'app/logs'),
        ('app/exportados', 'app/exportados'),
        ('app/output', 'app/output'),
        ('app/config', 'app/config'),

        # Archivos .keep
        ('app/db/.keep', 'app/db'),
        ('app/logs/.keep', 'app/logs'),
        ('app/exportados/.keep', 'app/exportados'),
        ('app/output/.keep', 'app/output'),
        ('app/config/.keep', 'app/config'),

        # Archivos de configuración
        ('app/excel_printer.db', 'app'),
        ('app/excel_printer_config.json', 'app'),
        
        # Verifica si el archivo plantilla_etiqueta.xlsx existe en la ruta indicada
        ('app/plantilla_etiqueta.xlsx', 'app')  # Asegúrate de que este archivo esté en app/
    ],
    hiddenimports=[
        'tkinter',
        'pandas',
        'openpyxl',
        'reportlab',
        'fpdf',
        'yaml',
        'PIL',
        'win32com.client' if sys.platform == "win32" else '',
        'win32print' if sys.platform == "win32" else '',
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
