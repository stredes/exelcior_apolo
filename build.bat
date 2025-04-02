@echo off
setlocal enabledelayedexpansion

echo ===============================
echo  🔧 Build automático Exelcior
echo ===============================

REM Carpetas necesarias
set DIRS=data db printer logs exportados

echo.
echo ▶ Verificando carpetas...
for %%D in (%DIRS%) do (
    if not exist "%%D" (
        echo ❌ Carpeta "%%D" no existe. Creándola...
        mkdir %%D
    )
    if not exist "%%D\\.keep" (
        echo 🧩 Añadiendo archivo .keep en %%D
        echo. > "%%D\\.keep"
    )
)

echo.
echo ▶ Ejecutando PyInstaller...
if exist build.log del build.log
pyinstaller main_app.spec > build.log 2>&1

REM Verificar resultado
if exist dist\ExelciorApolo\ExelciorApolo.exe (
    echo.
    echo ✅ Build exitoso. Ejecutable generado:
    echo    dist\ExelciorApolo\ExelciorApolo.exe
) else (
    echo.
    echo ❌ Build fallido. Revisa el archivo build.log para detalles.
    notepad build.log
)

echo.
pause
