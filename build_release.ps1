<#
 build_release.ps1 (PowerShell 5.1 compatible)
 Empaquetado automatizado (sin icono):
  - PyInstaller one-folder mediante .spec
  - Firma de EXEs/DLLs (opcional) con signtool
  - Instalador Inno Setup (ISCC)
  - Firma del instalador (opcional)
  - Checksums y reporte

 Ejemplo:
  powershell -ExecutionPolicy Bypass -File .\build_release.ps1 `
    -Version 1.4.0 `
    -AppName "Exelcior Apolo" `
    -ExeName "ExelciorApolo.exe" `
    -CreateIssIfMissing -RecreateVersionFile `
    -CertPfx "C:\certs\empresa_code_signing.pfx" `
    -CertPassword (Read-Host "Password PFX" -AsSecureString)
#>

[CmdletBinding()]
param(
  # --- Metadatos de la app ---
  [string]$Version = "1.4.0",
  [string]$AppName = "Exelcior Apolo",
  [string]$ExeName = "ExelciorApolo.exe",

  # --- Rutas clave ---
  [string]$SpecPath = "exelcior_apolo.spec",                # tu .spec sin icono
  [string]$VersionFile = "assets\version\exelcior_apolo_version.txt",
  [string]$InnoScript = "installer\exelcior_apolo.iss",

  # --- Herramientas ---
  [string]$PythonExe = "",                                   # autodetecta si vacío
  [string]$IsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",

  # --- Firma de código ---
  [string]$CertPfx = "",                                     # ruta PFX (opcional)
  [SecureString]$CertPassword,                               # SecureString recomendado
  [string]$CertSha1 = "",                                    # alternativa SHA1 en almacén
  [string]$TimestampUrl = "http://timestamp.sectigo.com",

  # --- Switches ---
  [switch]$CreateIssIfMissing,
  [switch]$RecreateVersionFile,
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

function Assert-File([string]$path, [string]$hint=""){
  if (-not (Test-Path -LiteralPath $path)) {
    throw "No se encontró: $path. $hint"
  }
}

# Ruta del script (compat PS 5.1)
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptRoot = Split-Path -Parent $ScriptPath
Set-Location -LiteralPath $ScriptRoot

# ===================== Detección de herramientas =====================

if (-not $PythonExe -or $PythonExe.Trim() -eq "") {
  $PythonExe = Get-CommandPath "py"
  if (-not $PythonExe) { $PythonExe = Get-CommandPath "python" }
  if (-not $PythonExe) { throw "No se encontró Python (py/python) en PATH. Instálalo o pasa -PythonExe." }
}
Write-Info "Python: $PythonExe"

$Signtool = Get-CommandPath "signtool"
if (-not $Signtool) { Write-Warn "signtool.exe no está en PATH. La firma se omitirá si no se configura." }

if (-not (Test-Path -LiteralPath $IsccPath)) {
  $isccTry = Get-CommandPath "iscc"
  if ($isccTry) {
    $IsccPath = $isccTry
    Write-Info "Usando ISCC en PATH: $IsccPath"
  }
}
Assert-File $IsccPath "Instala Inno Setup 6 o corrige -IsccPath."

# ===================== Preparación de carpetas =====================

$distDir = "dist\ExelciorApolo"
$outDir = "installer\output"
New-Item -ItemType Directory -Force -Path (Split-Path $VersionFile -Parent) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $InnoScript -Parent) | Out-Null
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# ===================== Archivo de versión (opcional) =====================

function New-VersionInfoContent([string]$v){
  if ($v -notmatch '^\d+\.\d+\.\d+$') { throw "Versión inválida: $v. Use x.y.z" }
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
  Write-Info "Generando archivo de versión: $VersionFile"
  (New-VersionInfoContent $Version) | Out-File -LiteralPath $VersionFile -Encoding UTF8 -Force
}
Assert-File $VersionFile "Falta archivo de versión."

# ===================== Inno Setup .iss (opcional) =====================

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

# ===================== Verificaciones previas =====================

Assert-File $SpecPath "Debe existir tu .spec (one-folder, sin icono, con 'version=$VersionFile')."

# ===================== Dependencias e instalación =====================

if (-not $NoPipInstall) {
  Write-Info "Instalando dependencias (pip) y PyInstaller..."
  & $PythonExe -m pip install --upgrade pip | Out-Host
  if (Test-Path -LiteralPath "requirements.txt") {
    & $PythonExe -m pip install -r requirements.txt | Out-Host
  }
  & $PythonExe -m pip install pyinstaller | Out-Host
}

# ===================== Build con PyInstaller =====================

Write-Info "Ejecutando PyInstaller con spec: $SpecPath"
& $PythonExe -m PyInstaller $SpecPath | Out-Host

Assert-File $distDir "No se generó la carpeta dist esperada: $distDir"
Assert-File (Join-Path $distDir $ExeName) "No se generó el ejecutable: $ExeName"

# ===================== Firma de binarios (opcional) =====================

function Convert-SecureStringToPlain([SecureString]$Sec){
  if (-not $Sec) { return "" }
  # Conversión controlada (en memoria) – requerido por signtool /p
  return ([System.Net.NetworkCredential]::new("", $Sec)).Password
}

function Invoke-CodeSign([string]$PathToSign){
  if (-not $Signtool) { throw "signtool no está disponible en PATH." }

  $sigArgs = @("sign","/fd","SHA256","/td","SHA256","/tr",$TimestampUrl)

  if ($CertPfx -and (Test-Path -LiteralPath $CertPfx)) {
    $sigArgs += @("/f",$CertPfx)
    $plain = Convert-SecureStringToPlain $CertPassword
    if ($plain -and $plain.Length -gt 0) { $sigArgs += @("/p",$plain) }
  } elseif ($CertSha1) {
    $sigArgs += @("/sha1",$CertSha1)
  } else {
    throw "No se especificó -CertPfx ni -CertSha1 para firmar."
  }

  $sigArgs += @($PathToSign)
  & $Signtool @sigArgs | Out-Host
}

function Invoke-CodeSignVerify([string]$PathToVerify){
  if (-not $Signtool) { return }
  & $Signtool verify /pa /all $PathToVerify | Out-Host
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

Write-Info "Compilando instalador con Inno Setup..."
& $IsccPath $InnoScript | Out-Host

$setupName = Join-Path $outDir ("ExelciorApolo_{0}_Setup.exe" -f $Version)
if (-not (Test-Path -LiteralPath $setupName)) {
  $last = Get-ChildItem -LiteralPath $outDir -Filter *.exe | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($last) { $setupName = $last.FullName }
}
Assert-File $setupName "No se generó el instalador. Revisa el log de Inno Setup."

# ===================== Firma del instalador (opcional) =====================

if (-not $SkipSignInstaller) {
  if ($Signtool -and ( ($CertPfx -and (Test-Path $CertPfx)) -or $CertSha1 )) {
    Write-Info "Firmando instalador: $setupName"
    Invoke-CodeSign $setupName
    Invoke-CodeSignVerify $setupName
    Write-OK "Firma del instalador completada."
  } else {
    Write-Warn "Omitiendo firma del instalador (no hay signtool/cert)."
  }
} else {
  Write-Warn "Firma del instalador omitida por -SkipSignInstaller."
}

# ===================== Checksums y reporte =====================

Write-Info "Generando checksums SHA256..."
$exeHash = Get-FileHash -LiteralPath (Join-Path $distDir $ExeName) -Algorithm SHA256
$setHash = Get-FileHash -LiteralPath $setupName -Algorithm SHA256
$hashFile = Join-Path $outDir ("checksums_{0}.txt" -f $Version)

@(
  "== Checksums $AppName v$Version =="
  "EXE (dist): $($exeHash.Hash)  *$($exeHash.Path)"
  "SETUP:      $($setHash.Hash)  *$($setHash.Path)"
) | Out-File -LiteralPath $hashFile -Encoding ascii -Force

Write-Host ""
Write-OK "BUILD COMPLETADO"
Write-Host "-----------------------------------------------"
Write-Host ("App:        {0}" -f $AppName)
Write-Host ("Versión:    {0}" -f $Version)
Write-Host ("Dist:       {0}" -f (Resolve-Path $distDir))
Write-Host ("EXE:        {0}" -f (Resolve-Path (Join-Path $distDir $ExeName)))
Write-Host ("Installer:  {0}" -f (Resolve-Path $setupName))
Write-Host ("Checksums:  {0}" -f (Resolve-Path $hashFile))
Write-Host "-----------------------------------------------"
