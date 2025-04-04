<<<<<<< HEAD
=======
# main_app.spec
>>>>>>> 05350b4 (ejecutable con modificacion v1.2.0 + reaadme + license)
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
<<<<<<< HEAD
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
=======
    ['main_app.py'],  # Archivo principal
    pathex=['.'],  # Ruta raíz del proyecto
    binaries=[],
    datas=[
        # Archivos de configuración y base de datos
        ('excel_printer_config.json', '.'),  # Archivo de configuración
        ('excel_printer.db', '.'),           # Base de datos
        # Incluir carpetas y archivos adicionales
        ('data/*', 'data'),  # Archivos dentro de 'data/'
        ('db/*', 'db'),      # Archivos dentro de 'db/'
        ('printer/*', 'printer'),  # Archivos dentro de 'printer/'
        ('logs/*', 'logs'),  # Archivos dentro de 'logs/'
        ('exportados/*', 'exportados'),  # Archivos dentro de 'exportados/'
    ],
    hiddenimports=[
        'tkinter',  # Interfaz gráfica
        'pandas',   # Procesamiento de datos
        'openpyxl', # Lectura de archivos Excel
        'reportlab',  # Generación de PDF
        'fpdf',        # Generación de PDF
        'yaml',         # Manejo de archivos YAML
        'PIL',          # Librería para trabajar con imágenes
        'utils',        # Directorio utils
        'config_dialog',  # Diálogo de configuración
        'excel_processor',  # Procesamiento de archivos Excel
        'printer',  # Impresión
        'herramientas',  # Herramientas adicionales
        'db',  # Base de datos
        'autoloader',  # Carga automática de archivos
        'logger_bod1',  # Registro de logs
    ],
    hookspath=[],  # Añadir cualquier hook personalizado si es necesario
    runtime_hooks=[],  # Si tienes hooks en tiempo de ejecución
    excludes=[],  # Excluir módulos si es necesario
>>>>>>> 05350b4 (ejecutable con modificacion v1.2.0 + reaadme + license)
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

    name='ExelciorApolo',  # Nombre del ejecutable
>>>>>>> 05350b4 (ejecutable con modificacion v1.2.0 + reaadme + license)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,

    console=False,  # Usa True si quieres que se vea la consola
    icon='assets/icono.ico',  # Asigna el ícono si tienes uno
>>>>>>> 05350b4 (ejecutable con modificacion v1.2.0 + reaadme + license)
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
