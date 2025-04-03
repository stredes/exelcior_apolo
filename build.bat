@echo off
setlocal enabledelayedexpansion

echo ===============================
echo  🚀 Build automático Exelcior
echo ===============================

REM Verificar carpetas requeridas
set DIRS=data db printer logs exportados assets

echo ▶ Verificando carpetas necesarias...
for %%D in (%DIRS%) do (
    if not exist "%%D" (
        echo ❌ Carpeta "%%D" no existe. Creándola...
        mkdir %%D
    )
    if not exist "%%D\\.keep" (
        echo. > "%%D\\.keep"
    )
)

REM Ejecutar PyInstaller
echo ▶ Compilando con PyInstaller...
if exist build.log del build.log
pyinstaller main_app.spec > build.log 2>&1

REM Verificar resultado
if exist dist\ExelciorApolo\ExelciorApolo.exe (
    echo ✅ Compilación exitosa:
    echo    dist\ExelciorApolo\ExelciorApolo.exe
) else (
    echo ❌ Fallo en la compilación. Revisa build.log
    notepad build.log
)

echo.
pause
