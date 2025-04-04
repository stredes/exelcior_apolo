@echo off
setlocal enabledelayedexpansion

echo ===============================

echo  🔧 Build automático Exelcior
echo ===============================

REM Verificar y crear carpetas necesarias
set DIRS=data db printer logs exportados

echo.
echo ▶ Verificando carpetas...
for %%D in (%DIRS%) do (
    if not exist "%%D" (
        echo ❌ Carpeta "%%D" no existe. Creándola...
        mkdir "%%D"
    )
    REM Agregar archivo .keep si la carpeta está vacía
    dir /b "%%D" | findstr . >nul || (
        echo 🧩 Añadiendo archivo .keep en %%D
>>>>>>> 05350b4 (ejecutable con modificacion v1.2.0 + reaadme + license)
        echo. > "%%D\\.keep"
    )
)


REM Limpiar build anterior (opcional)
echo.
echo ♻️  Limpiando builds previos...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo ▶ Ejecutando PyInstaller...
>>>>>>> 05350b4 (ejecutable con modificacion v1.2.0 + reaadme + license)
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
>>>>>>> 05350b4 (ejecutable con modificacion v1.2.0 + reaadme + license)
    notepad build.log
)

echo.
pause
