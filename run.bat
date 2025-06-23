@echo off
REM Exelcior Apolo v2.0.0 - Inicio Optimizado
title Exelcior Apolo v2.0.0

REM Optimizaciones de Python para arranque rápido
set PYTHONOPTIMIZE=1
set PYTHONDONTWRITEBYTECODE=1

cd /d "%~dp0"

echo Iniciando Exelcior Apolo v2.0.0...

REM Verificación rápida de Python (sin output)
python --version >nul 2>&1 || (
    echo ERROR: Python no encontrado
    pause & exit /b 1
)

REM Crear directorios mínimos necesarios
if not exist logs mkdir logs >nul 2>&1
if not exist exports mkdir exports >nul 2>&1

REM Verificar dependencias críticas rápidamente
python -c "import tkinter" >nul 2>&1 || (
    echo Instalando tkinter...
    pip install --quiet tk
)

REM Iniciar aplicación directamente
python src\main_dashboard.py

if errorlevel 1 (
    echo ERROR: Fallo al iniciar aplicacion
    pause
)
exit /b 0

