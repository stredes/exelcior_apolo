@echo off
setlocal enabledelayedexpansion

echo ===============================
echo  🔧 Build automático Exelcior Apolo
echo ===============================

REM Directorios esenciales
set DIRS=app\config app\db app\printer logs exportados

echo.
echo ▶ Verificando carpetas necesarias...
for %%D in (%DIRS%) do (
    if not exist "%%D" (
        echo ❌ Carpeta "%%D" no existe. Creándola...
        mkdir "%%D"
    )
    dir /b "%%D" | findstr . >nul || (
        echo 🧩 Añadiendo archivo .keep en %%D
        echo. > "%%D\\.keep"
    )
)

REM Limpieza previa
echo.
echo ♻️  Limpiando builds previos...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo ▶ Ejecutando PyInstaller...
if exist build.log del build.log
pyinstaller main_app.spec > build.log 2>&1

REM Verificación final
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
