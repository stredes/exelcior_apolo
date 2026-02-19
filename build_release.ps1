<#
 build_release.ps1 (PowerShell 5.1 compatible)

 Empaquetado automatizado:
  - PyInstaller (one-folder) usando exelcior_apolo.spec
  - Build opcional del mÃ³dulo Vale de Consumo (vale_consumo\build_utf8.ps1)
  - Copia de ValeConsumoBioplates dentro de dist\ExelciorApolo y dist\ExelciorApolo\vale_consumo
  - Firma opcional de EXEs/DLLs con signtool
  - Instalador Inno Setup (ISCC)
  - Firma opcional del instalador
  - Checksums SHA256

 Ejemplo:
   powershell -ExecutionPolicy Bypass -File .\build_release.ps1 `
     -Version 1.4.1 `
     -AppName "Exelcior Apolo" `
     -ExeName "ExelciorApolo.exe" `
     -CreateIssIfMissing -RecreateVersionFile `
     -CertPfx "C:\certs\empresa_code_signing.pfx" `
     -CertPassword (Read-Host "Password PFX" -AsSecureString)
#>

[CmdletBinding()]
param(
  # --- Metadatos de la app ---
  [string]$Version = "1.4.1",
  [string]$AppName = "Exelcior Apolo",
  [string]$ExeName = "ExelciorApolo.exe",

  # --- Rutas clave ---
  [string]$SpecPath = "exelcior_apolo.spec",                # .spec principal
  [string]$VersionFile = "assets\version\exelcior_apolo_version.txt",
  [string]$InnoScript = "installer\exelcior_apolo.iss",

  # --- Herramientas ---
  [string]$PythonExe = "",                                   # autodetecta si vacÃ­o
  [string]$IsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",

  # --- Firma de cÃ³digo ---
  [string]$CertPfx = "",                                     # ruta PFX (opcional)
  [SecureString]$CertPassword,                               # SecureString recomendado
  [string]$CertSha1 = "",                                    # alternativa SHA1 en almacÃ©n
  [string]$TimestampUrl = "https://timestamp.sectigo.com",

  # --- Switches ---
  [switch]$CreateIssIfMissing,
  [switch]$RecreateVersionFile,
  [switch]$SkipInstallerBuild,
  [switch]$SkipSignBinaries,
  [switch]$SkipSignInstaller,
  [switch]$NoPipInstall
)

# ===================== Helpers & Setup =====================

$ErrorActionPreference = "Stop"

function Write-Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-OK($m){ Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m){ Write-Host "[ERR]  $m" -ForegroundColor Red }

function Get-CommandPath([string]$name){
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Path } else { return $null }
}

function Get-PythonExeForVersion([string]$pyVer){
  try {
    $out = (& py -$pyVer -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1).Trim()
    if ($out -and (Test-Path -LiteralPath $out)) { return $out }
  } catch {}
  return $null
}

function Assert-File([string]$path, [string]$hint=""){
  if (-not (Test-Path -LiteralPath $path)) {
    throw "No se encontró: $path. $hint"
  }
  return $true
}

function Assert-LastExitCode([string]$step){
  if ($LASTEXITCODE -ne 0) {
    throw "$step falló con código de salida $LASTEXITCODE."
  }
}

function Test-PythonImport([string]$pythonExe, [string]$moduleName){
  try {
    & $pythonExe -c "import $moduleName" *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Install-PythonPackageIfMissing([string]$pythonExe, [string]$moduleName, [string]$pipName){
  if (Test-PythonImport $pythonExe $moduleName) {
    return
  }
  Write-Warn "Módulo faltante '$moduleName'. Intentando instalar paquete '$pipName'..."
  & $pythonExe -m pip install $pipName | Out-Host
  Assert-LastExitCode "pip install $pipName"
  if (-not (Test-PythonImport $pythonExe $moduleName)) {
    throw "No se pudo importar '$moduleName' después de instalar '$pipName'."
  }
  Write-OK "Dependencia validada: $moduleName"
}

# Ruta del script (compat PS 5.1)
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptRoot = Split-Path -Parent $ScriptPath
Set-Location -LiteralPath $ScriptRoot

# ===================== DetecciÃ³n de herramientas =====================

if (-not $PythonExe -or $PythonExe.Trim() -eq "") {
  $localVenvPython = Join-Path $ScriptRoot ".venv\Scripts\python.exe"
  if (Test-Path -LiteralPath $localVenvPython) {
    $PythonExe = $localVenvPython
  } else {
    $PythonExe = Get-CommandPath "python"
    if (-not $PythonExe) { $PythonExe = Get-CommandPath "py" }
    if (-not $PythonExe) { throw "No se encontró Python (ni .venv\\Scripts\\python.exe, ni 'python', ni 'py')." }
  }
}
Write-Info "Python: $PythonExe"
$PythonVersion = (& $PythonExe -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null | Select-Object -First 1).Trim()
if ($PythonVersion) {
  Write-Info "Python version: $PythonVersion"
  try {
    if ([version]("$PythonVersion.0") -ge [version]"3.13.0") {
      Write-Warn "Python $PythonVersion puede no tener ruedas precompiladas para algunas dependencias (ej. numpy)."
      if (-not $PSBoundParameters.ContainsKey('PythonExe')) {
        $py312 = Get-PythonExeForVersion "3.12"
        $py311 = Get-PythonExeForVersion "3.11"
        $fallback = if ($py312) { $py312 } elseif ($py311) { $py311 } else { $null }
        if ($fallback) {
          Write-Warn "Cambiando automáticamente a Python compatible: $fallback"
          $PythonExe = $fallback
          $PythonVersion = (& $PythonExe -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null | Select-Object -First 1).Trim()
          Write-Info "Python final para build: $PythonExe (v$PythonVersion)"
        } else {
          Write-Warn "No se encontró Python 3.12/3.11 en el sistema. Si falla numpy, instala Python 3.12 y vuelve a ejecutar."
        }
      }
    }
  } catch {
    # sin-op: solo advertencia informativa
  }
}

$Signtool = Get-CommandPath "signtool"
if (-not $Signtool) { Write-Warn "signtool.exe no estÃ¡ en PATH. La firma se omitirÃ¡ si no se configura." }

if (-not (Test-Path -LiteralPath $IsccPath)) {
  $isccTry = Get-CommandPath "iscc"
  if ($isccTry) {
    $IsccPath = $isccTry
    Write-Info "Usando ISCC en PATH: $IsccPath"
  }
}
$CanBuildInstaller = $true
if ($SkipInstallerBuild) {
  $CanBuildInstaller = $false
  Write-Warn "Instalador omitido por parámetro -SkipInstallerBuild."
} elseif (-not (Test-Path -LiteralPath $IsccPath)) {
  $CanBuildInstaller = $false
  Write-Warn "No se encontró ISCC.exe; se omitirá la generación del instalador. Instala Inno Setup 6 o corrige -IsccPath."
}

# ===================== PreparaciÃ³n de carpetas =====================

$distDir = "dist\ExelciorApolo"
$outDir = "installer\output"
New-Item -ItemType Directory -Force -Path (Split-Path $VersionFile -Parent) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $InnoScript -Parent) | Out-Null
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# ===================== Archivo de versiÃ³n =====================

function New-VersionInfoContent([string]$v){
  if ($v -notmatch '^\d+\.\d+\.\d+$') { throw "VersiÃ³n invÃ¡lida: $v. Use x.y.z" }
@"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($($v.Split('.')[0]), $($v.Split('.')[1]), $($v.Split('.')[2]), 0),
    prodvers=($($v.Split('.')[0]), $($v.Split('.')[1]), $($v.Split('.')[2]), 0),
    mask=0x3f, flags=0x0, OS=0x4, fileType=0x1, subtype=0x0, date=(0,0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName','AMILAB / Exelcior'),
        StringStruct('FileDescription','$AppName'),
        StringStruct('FileVersion','$v'),
        StringStruct('OriginalFilename','$ExeName'),
        StringStruct('ProductName','$AppName'),
        StringStruct('ProductVersion','$v'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation',[1033,1200])])
  ]
)
"@
}

if ($RecreateVersionFile -or -not (Test-Path -LiteralPath $VersionFile)) {
  Write-Info "Generando archivo de versiÃ³n: $VersionFile"
  (New-VersionInfoContent $Version) | Out-File -LiteralPath $VersionFile -Encoding UTF8 -Force
}
Assert-File $VersionFile "Falta archivo de versiÃ³n."

# ===================== Inno Setup .iss =====================

$appIdPath = "installer\AppId.txt"
if (-not (Test-Path -LiteralPath $appIdPath)) {
  (New-Guid).Guid | Out-File -LiteralPath $appIdPath -Encoding ascii -Force
}
$AppId = (Get-Content -LiteralPath $appIdPath -Raw).Trim()

function New-IssContent{
@"
#define AppName "$AppName"
#define AppVersion "$Version"
#define AppPublisher "AMILAB / Exelcior"
#define AppExeName "$ExeName"

[Setup]
AppId={{$AppId}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
LicenseFile=installer\LICENSE.txt
OutputDir=installer\output
OutputBaseFilename=ExelciorApolo_{#AppVersion}_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\ExelciorApolo\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Flags: nowait postinstall skipifsilent
"@
}

if ($CreateIssIfMissing -or -not (Test-Path -LiteralPath $InnoScript)) {
  Write-Info "Generando script Inno Setup: $InnoScript"
  (New-IssContent) | Out-File -LiteralPath $InnoScript -Encoding UTF8 -Force
  $lic = "installer\LICENSE.txt"
  if (-not (Test-Path -LiteralPath $lic)) {
    "Licencia de ejemplo - reemplazar por la licencia real." | Out-File -LiteralPath $lic -Encoding UTF8 -Force
  }
}
Assert-File $InnoScript "Falta el script de Inno Setup. Ejecuta con -CreateIssIfMissing para crearlo."
$lic = "installer\LICENSE.txt"
Assert-File $lic "Falta installer\LICENSE.txt (requerido por el script .iss)."

# ===================== Verificaciones previas =====================

Assert-File $SpecPath "Debe existir tu .spec (one-folder, con version e icono configurados)."

# ===================== Dependencias e instalaciÃ³n =====================

if (-not $NoPipInstall) {
  Write-Info "Instalando dependencias (pip) y PyInstaller..."
  $pipStepFailed = $false
  try {
    & $PythonExe -m pip install --upgrade pip | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade falló con código de salida $LASTEXITCODE." }
    if (Test-Path -LiteralPath "requirements.txt") {
      & $PythonExe -m pip install -r requirements.txt | Out-Host
      if ($LASTEXITCODE -ne 0) {
        $pipStepFailed = $true
        Write-Warn "pip install -r requirements.txt falló con código de salida $LASTEXITCODE."
      }
    }
    & $PythonExe -m pip install pyinstaller | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller falló con código de salida $LASTEXITCODE." }
  } catch {
    $pipStepFailed = $true
    Write-Warn "Falló instalación de dependencias con pip: $($_.Exception.Message)"
    Write-Warn "Se continuará con el build. Si falta algún módulo al empaquetar, usa -NoPipInstall o instala una versión de Python compatible (recomendado 3.11/3.12)."
  }
  if (-not $pipStepFailed) {
    Write-OK "Dependencias instaladas correctamente."
  }
}

# Validación mínima de dependencias runtime antes de empaquetar.
# Evita generar un EXE que luego falle por ModuleNotFoundError.
$runtimeDeps = @(
  @{ Module = "sqlalchemy"; Pip = "SQLAlchemy" },
  @{ Module = "pandas"; Pip = "pandas" },
  @{ Module = "openpyxl"; Pip = "openpyxl" },
  @{ Module = "odf"; Pip = "odfpy" },
  @{ Module = "reportlab"; Pip = "reportlab" },
  @{ Module = "PIL"; Pip = "pillow" }
)

# Impresión Windows (Excel COM / printto) depende de pywin32.
$isWindowsHost = $env:OS -eq "Windows_NT"
if ($isWindowsHost) {
  $runtimeDeps += @(
    @{ Module = "pythoncom"; Pip = "pywin32" },
    @{ Module = "win32print"; Pip = "pywin32" },
    @{ Module = "win32api"; Pip = "pywin32" },
    @{ Module = "win32com.client"; Pip = "pywin32" }
  )
}
foreach ($dep in $runtimeDeps) {
  Install-PythonPackageIfMissing -pythonExe $PythonExe -moduleName $dep.Module -pipName $dep.Pip
}

# ===================== Build con PyInstaller =====================

# Build opcional de Vale de Consumo (exe separado)
$valeBuildScript = Join-Path $ScriptRoot 'vale_consumo\build_utf8.ps1'
if (Test-Path -LiteralPath $valeBuildScript) {
  Write-Info "Construyendo ValeConsumoBioplates (vale_consumo\build_utf8.ps1)..."
  try {
    & $valeBuildScript -Task package
    if ($LASTEXITCODE -ne 0) {
      Write-Warn "build_utf8.ps1 devolviÃ³ cÃ³digo $LASTEXITCODE; se continuarÃ¡ sin empaquetar Vale de Consumo."
    }
  } catch {
    Write-Warn "Error al ejecutar build_utf8.ps1: $($_.Exception.Message)"
  }
} else {
  Write-Warn "No se encontrÃ³ vale_consumo\build_utf8.ps1; se omitirÃ¡ Vale de Consumo."
}

Write-Info "Ejecutando PyInstaller con spec: $SpecPath"
if (Test-Path -LiteralPath $distDir) {
  Write-Info "Limpiando salida previa de PyInstaller: $distDir"
  Remove-Item -LiteralPath $distDir -Recurse -Force
}
& $PythonExe -m PyInstaller -y $SpecPath | Out-Host
Assert-LastExitCode "PyInstaller"

Assert-File $distDir "No se generÃ³ la carpeta dist esperada: $distDir"
Assert-File (Join-Path $distDir $ExeName) "No se generÃ³ el ejecutable: $ExeName"
$sqlalchemyDistPath = Join-Path $distDir "_internal\sqlalchemy"
Assert-File $sqlalchemyDistPath "Build inválido: no se incluyó SQLAlchemy en el paquete. Revisa el entorno Python usado para PyInstaller."

# Copiar artefactos de Vale de Consumo al dist principal (para integraciÃ³n desde el menÃº)
$valeDistRoot = Join-Path $ScriptRoot 'vale_consumo\dist'
if (Test-Path -LiteralPath $valeDistRoot) {
  $valeTarget = Join-Path $distDir 'vale_consumo'
  New-Item -ItemType Directory -Force -Path $valeTarget | Out-Null
  try {
    # Copia todo el dist de vales a una subcarpeta
    Copy-Item -LiteralPath (Join-Path $valeDistRoot '*') -Destination $valeTarget -Recurse -Force
    # Copia el exe principal tambiÃ©n junto al ejecutable principal de Exelcior
    $valeExe = Join-Path $valeDistRoot 'ValeConsumoBioplates.exe'
    if (Test-Path -LiteralPath $valeExe) {
      Copy-Item -LiteralPath $valeExe -Destination (Join-Path $distDir 'ValeConsumoBioplates.exe') -Force
    }
    Write-Info "ValeConsumoBioplates copiado a: $valeTarget y al root de dist."
  } catch {
    Write-Warn "No se pudieron copiar los archivos de Vale de Consumo: $($_.Exception.Message)"
  }
} else {
  Write-Warn "No se encontrÃ³ vale_consumo\dist; el instalador no incluirÃ¡ ValeConsumoBioplates."
}

# ===================== Firma de binarios (opcional) =====================

function Convert-SecureStringToPlain([SecureString]$Sec){
  if (-not $Sec) { return "" }
  # ConversiÃ³n controlada (en memoria), requerido por signtool /p
  return ([System.Net.NetworkCredential]::new("", $Sec)).Password
}

function Invoke-CodeSign([string]$PathToSign){
  if (-not $Signtool) { throw "signtool no estÃ¡ disponible en PATH." }

  $sigArgs = @("sign","/fd","SHA256","/td","SHA256","/tr",$TimestampUrl)

  if ($CertPfx -and (Test-Path -LiteralPath $CertPfx)) {
    $sigArgs += @("/f",$CertPfx)
    $plain = Convert-SecureStringToPlain $CertPassword
    if ($plain -and $plain.Length -gt 0) { $sigArgs += @("/p",$plain) }
  } elseif ($CertSha1) {
    $sigArgs += @("/sha1",$CertSha1)
  } else {
    throw "No se especificÃ³ -CertPfx ni -CertSha1 para firmar."
  }

  $sigArgs += @($PathToSign)
  & $Signtool @sigArgs | Out-Host
  Assert-LastExitCode "Firma de código ($PathToSign)"
}

function Invoke-CodeSignVerify([string]$PathToVerify){
  if (-not $Signtool) { return }
  & $Signtool verify /pa /all $PathToVerify | Out-Host
  Assert-LastExitCode "Verificación de firma ($PathToVerify)"
}

if (-not $SkipSignBinaries) {
  if ($Signtool -and ( ($CertPfx -and (Test-Path $CertPfx)) -or $CertSha1 )) {
    Write-Info "Firmando binarios en: $distDir"
    Get-ChildItem -LiteralPath $distDir -Recurse -Include *.exe,*.dll | ForEach-Object {
      Invoke-CodeSign $_.FullName
      Invoke-CodeSignVerify $_.FullName
    }
    Write-OK "Firma de binarios completada."
  } else {
    Write-Warn "Omitiendo firma de binarios (no hay signtool/cert)."
  }
} else {
  Write-Warn "Firma de binarios omitida por -SkipSignBinaries."
}

# ===================== Compilar instalador Inno Setup =====================

$setupName = $null
if ($CanBuildInstaller) {
  Write-Info "Compilando instalador con Inno Setup..."
  & $IsccPath $InnoScript | Out-Host
  Assert-LastExitCode "Inno Setup (ISCC)"

  $setupName = Join-Path $outDir ("ExelciorApolo_{0}_Setup.exe" -f $Version)
  if (-not (Test-Path -LiteralPath $setupName)) {
    $last = Get-ChildItem -LiteralPath $outDir -Filter *.exe | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($last) { $setupName = $last.FullName }
  }
  Assert-File $setupName "No se generÃ³ el instalador. Revisa el log de Inno Setup."
} else {
  Write-Warn "Se omite compilación de instalador."
}

# ===================== Firma del instalador (opcional) =====================

if (-not $SkipSignInstaller -and $CanBuildInstaller -and $setupName) {
  if ($Signtool -and ( ($CertPfx -and (Test-Path $CertPfx)) -or $CertSha1 )) {
    Write-Info "Firmando instalador: $setupName"
    Invoke-CodeSign $setupName
    Invoke-CodeSignVerify $setupName
    Write-OK "Firma del instalador completada."
  } else {
    Write-Warn "Omitiendo firma del instalador (no hay signtool/cert)."
  }
} else {
  if ($SkipSignInstaller) {
    Write-Warn "Firma del instalador omitida por -SkipSignInstaller."
  } else {
    Write-Warn "Firma del instalador omitida (no se generó instalador)."
  }
}

# ===================== Checksums y reporte =====================

Write-Info "Generando checksums SHA256..."
$exeHash = Get-FileHash -LiteralPath (Join-Path $distDir $ExeName) -Algorithm SHA256
$hashFile = Join-Path $outDir ("checksums_{0}.txt" -f $Version)

$hashLines = @(
  "== Checksums $AppName v$Version ==",
  "EXE (dist): $($exeHash.Hash)  *$($exeHash.Path)"
)
if ($CanBuildInstaller -and $setupName -and (Test-Path -LiteralPath $setupName)) {
  $setHash = Get-FileHash -LiteralPath $setupName -Algorithm SHA256
  $hashLines += "SETUP:      $($setHash.Hash)  *$($setHash.Path)"
}
$hashLines | Out-File -LiteralPath $hashFile -Encoding ascii -Force

Write-Host ""
Write-OK "BUILD COMPLETADO"
Write-Host "-----------------------------------------------"
Write-Host ("App:        {0}" -f $AppName)
Write-Host ("VersiÃ³n:    {0}" -f $Version)
Write-Host ("Dist:       {0}" -f (Resolve-Path $distDir))
Write-Host ("EXE:        {0}" -f (Resolve-Path (Join-Path $distDir $ExeName)))
if ($CanBuildInstaller -and $setupName -and (Test-Path -LiteralPath $setupName)) {
  Write-Host ("Installer:  {0}" -f (Resolve-Path $setupName))
} else {
  Write-Host ("Installer:  {0}" -f "OMITIDO")
}
Write-Host ("Checksums:  {0}" -f (Resolve-Path $hashFile))
Write-Host "-----------------------------------------------"




