@echo off
REM Exelcior Apolo v2.0.0 - Inicio Optimizado
REM Optimizado para arranque rápido y eficiente

title Exelcior Apolo v2.0.0 - Iniciando...

REM Configurar variables de entorno para optimización
set PYTHONOPTIMIZE=1
set PYTHONDONTWRITEBYTECODE=1
set PYTHONUNBUFFERED=1

REM Cambiar al directorio del script
cd /d "%~dp0"

echo.
echo ========================================
echo   EXELCIOR APOLO v2.0.0 - INICIO RAPIDO
echo ========================================
echo.

REM Verificar si Python está disponible (sin mostrar output)
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en el sistema
    echo.
    echo Instale Python 3.8+ desde: https://python.org
    echo.
    pause
    exit /b 1
)

REM Verificar dependencias críticas rápidamente
echo [INFO] Verificando dependencias criticas...
python -c "import tkinter, pandas, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Instalando dependencias faltantes...
    pip install --quiet --no-warn-script-location pandas openpyxl pillow reportlab tkinter tkcalendar
    if errorlevel 1 (
        echo [ERROR] Error instalando dependencias
        pause
        exit /b 1
    )
)

REM Crear directorios necesarios si no existen
if not exist "logs" mkdir logs >nul 2>&1
if not exist "exports" mkdir exports >nul 2>&1
if not exist "exports\pdf" mkdir exports\pdf >nul 2>&1
if not exist "config" mkdir config >nul 2>&1

echo [INFO] Iniciando Exelcior Apolo Dashboard...
echo.

REM Iniciar aplicación con dashboard optimizado
python src\main_dashboard.py

REM Si hay error, mostrar mensaje
if errorlevel 1 (
    echo.
    echo [ERROR] Error al iniciar la aplicacion
    echo.
    echo Posibles soluciones:
    echo 1. Verificar que Python 3.8+ este instalado
    echo 2. Ejecutar como administrador
    echo 3. Verificar permisos de escritura en el directorio
    echo.
    pause
    exit /b 1
)

REM Mensaje de cierre normal
echo.
echo [INFO] Exelcior Apolo cerrado correctamente
echo.
timeout /t 2 /nobreak >nul
exit /b 0

