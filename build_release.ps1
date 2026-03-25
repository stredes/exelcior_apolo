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
   powershell -ExecutionPolicy Bypass -File .\build_release.ps1
#>

[CmdletBinding()]
param(
  # --- Metadatos de la app ---
  [string]$Version = "",
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
  [switch]$NoPipInstall,

  # --- Publicación opcional en GitHub ---
  [switch]$SkipGitHubPublish,
  [string]$GitTag = "",
  [string]$GitRemote = "origin",
  [string]$GitHubRepo = "",
  [string]$GitHubToken = "",
  [string]$ReleaseTitle = "",
  [string]$ReleaseNotesFile = "",
  [switch]$DraftRelease,
  [switch]$Prerelease,
  [switch]$SkipGitTagPush,
  [switch]$AllowDirtyWorktree,
  [switch]$SkipAutoVersion,
  [switch]$SkipAutoCommit
)

# ===================== Helpers & Setup =====================

$ErrorActionPreference = "Stop"

function Write-Info($m){ Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-OK($m){ Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m){ Write-Host "[ERR]  $m" -ForegroundColor Red }

function Invoke-Step([scriptblock]$Action, [string]$Step){
  & $Action
  Assert-LastExitCode $Step
}

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

function Get-TextFileIfExists([string]$path){
  if ($path -and (Test-Path -LiteralPath $path)) {
    return (Get-Content -LiteralPath $path -Raw -Encoding UTF8)
  }
  return ""
}

function Get-GitHubTokenValue{
  if ($GitHubToken -and $GitHubToken.Trim()) { return $GitHubToken.Trim() }
  if ($env:GITHUB_TOKEN -and $env:GITHUB_TOKEN.Trim()) { return $env:GITHUB_TOKEN.Trim() }
  if ($env:GH_TOKEN -and $env:GH_TOKEN.Trim()) { return $env:GH_TOKEN.Trim() }
  return ""
}

function Get-GitHubRepoFromRemote([string]$remoteName){
  try {
    $url = (& git remote get-url $remoteName 2>$null | Select-Object -First 1).Trim()
    if (-not $url) { return "" }
    if ($url -match 'github\.com[:/](.+?)(?:\.git)?$') {
      return $matches[1]
    }
  } catch {}
  return ""
}

function Get-ReleaseTag([string]$version){
  if ($GitTag -and $GitTag.Trim()) { return $GitTag.Trim() }
  return "v$version"
}

function Get-CurrentGitBranch{
  $branch = (& git branch --show-current 2>$null | Select-Object -First 1).Trim()
  Assert-LastExitCode "git branch --show-current"
  if (-not $branch) { throw "No se pudo determinar la rama actual." }
  return $branch
}

function Test-GitWorktreeDirty{
  $status = (& git status --porcelain 2>$null)
  Assert-LastExitCode "git status --porcelain"
  return [bool]$status
}

function Get-VersionFromTag([string]$tag){
  $clean = ($tag -replace '^[vV]', '').Trim()
  if ($clean -match '^\d+\.\d+\.\d+$') { return $clean }
  return $null
}

function Get-LatestGitVersion{
  try {
    & git fetch --tags $GitRemote | Out-Host
    if ($LASTEXITCODE -ne 0) {
      Write-Warn "No se pudieron actualizar tags desde '$GitRemote'. Se usarán los tags locales."
    }
  } catch {
    Write-Warn "git fetch --tags falló: $($_.Exception.Message)"
  }

  $tags = @(& git tag --list "v*" 2>$null)
  Assert-LastExitCode "git tag --list v*"
  $versions = @()
  foreach ($tag in $tags) {
    $ver = Get-VersionFromTag ([string]$tag)
    if ($ver) { $versions += $ver }
  }
  if (-not $versions -or $versions.Count -eq 0) { return "1.0.0" }
  return ($versions | Sort-Object {
    $parts = $_.Split('.') | ForEach-Object { [int]$_ }
    '{0:D6}.{1:D6}.{2:D6}' -f $parts[0], $parts[1], $parts[2]
  } | Select-Object -Last 1)
}

function Get-NextPatchVersion([string]$baseVersion){
  if ($baseVersion -notmatch '^\d+\.\d+\.\d+$') {
    throw "Versión base inválida para autoincremento: $baseVersion"
  }
  $parts = $baseVersion.Split('.') | ForEach-Object { [int]$_ }
  return ("{0}.{1}.{2}" -f $parts[0], $parts[1], ($parts[2] + 1))
}

function Update-IssVersionDefines([string]$issPath, [string]$version, [string]$appName, [string]$exeName){
  Assert-File $issPath "Falta script de Inno Setup."
  $content = Get-Content -LiteralPath $issPath -Raw -Encoding UTF8
  $content = [regex]::Replace($content, '(?m)^#define AppName ".*"$', ('#define AppName "{0}"' -f $appName))
  $content = [regex]::Replace($content, '(?m)^#define AppVersion ".*"$', ('#define AppVersion "{0}"' -f $version))
  $content = [regex]::Replace($content, '(?m)^#define AppExeName ".*"$', ('#define AppExeName "{0}"' -f $exeName))
  Set-Content -LiteralPath $issPath -Value $content -Encoding UTF8
}

function Invoke-GitHubApi([string]$Method, [string]$Url, [string]$Token, $Body = $null, [string]$ContentType = "application/json"){
  $headers = @{
    Authorization = "Bearer $Token"
    Accept = "application/vnd.github+json"
    "User-Agent" = "ExelciorApoloBuildRelease/1.0"
  }
  $params = @{
    Method = $Method
    Uri = $Url
    Headers = $headers
  }
  if ($null -ne $Body) {
    $params["Body"] = $Body
    $params["ContentType"] = $ContentType
  }
  return Invoke-RestMethod @params
}

function Assert-CleanGitWorktree{
  if (Test-GitWorktreeDirty) {
    throw "El árbol de trabajo tiene cambios sin commit. Usa un commit limpio o pasa -AllowDirtyWorktree."
  }
}

function Publish-GitBranch([string]$remoteName, [string]$branchName){
  Write-Info "Empujando rama '$branchName' a '$remoteName'..."
  & git push $remoteName $branchName | Out-Host
  Assert-LastExitCode "git push $remoteName $branchName"
}

function Save-ReleaseCommit([string]$version, [string]$remoteName){
  $branchName = Get-CurrentGitBranch
  if (Test-GitWorktreeDirty) {
    Write-Info "Creando commit automático de release para v$version..."
    & git add -A | Out-Host
    Assert-LastExitCode "git add -A"
    & git commit -m "release: v$version" | Out-Host
    Assert-LastExitCode "git commit release: v$version"
  } else {
    Write-Info "No hay cambios pendientes para commit automático."
  }
  Publish-GitBranch -remoteName $remoteName -branchName $branchName
}

function Publish-GitTag([string]$tagName, [string]$remoteName){
  $existing = (& git tag --list $tagName | Select-Object -First 1).Trim()
  Assert-LastExitCode "git tag --list"
  if (-not $existing) {
    Write-Info "Creando tag local: $tagName"
    & git tag $tagName
    Assert-LastExitCode "git tag $tagName"
  } else {
    Write-Info "El tag local ya existe: $tagName"
  }
  if (-not $SkipGitTagPush) {
    Write-Info "Empujando tag a remoto '$remoteName'..."
    & git push $remoteName $tagName | Out-Host
    Assert-LastExitCode "git push $remoteName $tagName"
  } else {
    Write-Warn "Push del tag omitido por -SkipGitTagPush."
  }
}

function Set-GitHubRelease([string]$repo, [string]$token, [string]$tagName, [string]$title, [string]$notes, [bool]$isDraft, [bool]$isPrerelease){
  $baseApi = "https://api.github.com/repos/$repo"
  $release = $null
  try {
    $release = Invoke-GitHubApi -Method "GET" -Url "$baseApi/releases/tags/$tagName" -Token $token
    Write-Info "Release existente encontrada para tag $tagName."
  } catch {
    Write-Info "No existe release para $tagName. Se creará una nueva."
  }

  $payloadObj = @{
    tag_name = $tagName
    name = $title
    body = $notes
    draft = $isDraft
    prerelease = $isPrerelease
  }
  $payloadJson = $payloadObj | ConvertTo-Json -Depth 5

  if ($release -and $release.id) {
    $release = Invoke-GitHubApi -Method "PATCH" -Url "$baseApi/releases/$($release.id)" -Token $token -Body $payloadJson
  } else {
    $release = Invoke-GitHubApi -Method "POST" -Url "$baseApi/releases" -Token $token -Body $payloadJson
  }
  return $release
}

function Remove-ExistingReleaseAsset([string]$repo, [string]$token, $release, [string]$assetName){
  if (-not $release -or -not $release.assets) { return }
  foreach ($asset in $release.assets) {
    if ($asset.name -eq $assetName) {
      Write-Info "Eliminando asset existente del release: $assetName"
      Invoke-GitHubApi -Method "DELETE" -Url "https://api.github.com/repos/$repo/releases/assets/$($asset.id)" -Token $token
    }
  }
}

function Send-ReleaseAsset([string]$repo, [string]$token, $release, [string]$filePath){
  Assert-File $filePath "Asset faltante para GitHub Release."
  $assetName = Split-Path -Leaf $filePath
  Remove-ExistingReleaseAsset -repo $repo -token $token -release $release -assetName $assetName
  $uploadUrl = [string]$release.upload_url
  if (-not $uploadUrl) { throw "La release no devolvió upload_url." }
  $uploadUrl = $uploadUrl -replace '\{\?name,label\}$', ''
  $uploadUrl = "$uploadUrl?name=$([System.Uri]::EscapeDataString($assetName))"

  $headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "User-Agent" = "ExelciorApoloBuildRelease/1.0"
  }
  Write-Info "Subiendo asset al release: $assetName"
  Invoke-RestMethod -Method "POST" -Uri $uploadUrl -Headers $headers -InFile $filePath -ContentType "application/octet-stream" | Out-Null
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

if (-not $SkipGitHubPublish) {
  if (-not $AllowDirtyWorktree -and $SkipAutoCommit) {
    Assert-CleanGitWorktree
  } elseif ($AllowDirtyWorktree) {
    Write-Warn "Publicando con árbol de trabajo sucio por -AllowDirtyWorktree."
  }
}

if (-not $Version -or $Version.Trim() -eq "") {
  if ($SkipAutoVersion) {
    throw "Debes indicar -Version cuando usas -SkipAutoVersion."
  }
  $latestVersion = Get-LatestGitVersion
  $Version = Get-NextPatchVersion $latestVersion
  Write-Info "Versión autoincrementada: $Version"
} else {
  Write-Info "Versión manual: $Version"
}

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

if ($RecreateVersionFile -or -not (Test-Path -LiteralPath $VersionFile) -or (-not $PSBoundParameters.ContainsKey('Version'))) {
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
CloseApplications=yes
RestartApplications=no
CloseApplicationsFilter=*.exe

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
Update-IssVersionDefines -issPath $InnoScript -version $Version -appName $AppName -exeName $ExeName
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
  @{ Module = "PIL"; Pip = "pillow" },
  @{ Module = "requests"; Pip = "requests" }
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

# Validación de módulos internos críticos antes de empaquetar.
# Evita generar un build que arranca pero falla por imports faltantes/refactors.
$appRuntimeModules = @(
  "app.main_app",
  "app.services.file_service",
  "app.gui.etiqueta_editor",
  "app.gui.inventario_view",
  "app.gui.printer_admin"
)
foreach ($mod in $appRuntimeModules) {
  if (-not (Test-PythonImport $PythonExe $mod)) {
    throw "Import interno fallido antes del build: '$mod'. Revisa errores de código o rutas."
  }
}
Write-OK "Imports internos validados (incluye administración de impresoras)."

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

# ===================== Publicación GitHub (opcional) =====================

$publishedRelease = $null
if (-not $SkipGitHubPublish) {
  if (-not $SkipAutoCommit) {
    Save-ReleaseCommit -version $Version -remoteName $GitRemote
  } elseif (-not $AllowDirtyWorktree) {
    Assert-CleanGitWorktree
  }

  Write-Info "Preparando publicación en GitHub..."
  $tokenValue = Get-GitHubTokenValue
  if (-not $tokenValue) {
    throw "Falta token de GitHub. Usa -GitHubToken o define GITHUB_TOKEN / GH_TOKEN."
  }

  $repoValue = $GitHubRepo
  if (-not $repoValue -or -not $repoValue.Trim()) {
    $repoValue = Get-GitHubRepoFromRemote $GitRemote
  }
  if (-not $repoValue) {
    throw "No se pudo resolver el repositorio GitHub. Usa -GitHubRepo owner/repo."
  }

  $tagName = Get-ReleaseTag $Version
  $titleValue = if ($ReleaseTitle -and $ReleaseTitle.Trim()) { $ReleaseTitle.Trim() } else { "$AppName $Version" }
  $notesValue = Get-TextFileIfExists $ReleaseNotesFile
  if (-not $notesValue) {
    $notesValue = "Release automatizada para $AppName v$Version."
  }

  Publish-GitTag -tagName $tagName -remoteName $GitRemote
  $publishedRelease = Set-GitHubRelease `
    -repo $repoValue `
    -token $tokenValue `
    -tagName $tagName `
    -title $titleValue `
    -notes $notesValue `
    -isDraft ([bool]$DraftRelease) `
    -isPrerelease ([bool]$Prerelease)

  if ($CanBuildInstaller -and $setupName -and (Test-Path -LiteralPath $setupName)) {
    Send-ReleaseAsset -repo $repoValue -token $tokenValue -release $publishedRelease -filePath $setupName
  } else {
    Write-Warn "No hay instalador para subir al release."
  }
  Send-ReleaseAsset -repo $repoValue -token $tokenValue -release $publishedRelease -filePath $hashFile
  Write-OK "Publicación en GitHub completada."
}

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
if ($publishedRelease -and $publishedRelease.html_url) {
  Write-Host ("Release:    {0}" -f $publishedRelease.html_url)
}
Write-Host "-----------------------------------------------"




