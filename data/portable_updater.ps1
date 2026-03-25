$ErrorActionPreference = 'Stop'
$cfg = Get-Content -LiteralPath '__CONFIG_PATH__' -Raw | ConvertFrom-Json
$zipPath = [string]$cfg.zip_path
$extractDir = [string]$cfg.extract_dir
$installDir = [string]$cfg.install_dir
$exeName = [string]$cfg.exe_name
$currentPid = [int]$cfg.current_pid
$targetVersion = [string]$cfg.target_version
$statePath = [string]$cfg.state_path
$desktopNames = @($cfg.desktop_names)
$parentDir = Split-Path -Parent $installDir
$backupDir = Join-Path $parentDir ((Split-Path -Leaf $installDir) + '_backup')
$stagingDir = Join-Path $parentDir ((Split-Path -Leaf $installDir) + '_staging')
$logPath = '__LOG_PATH__'

function Write-Log([string]$message) {
  $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Add-Content -LiteralPath $logPath -Value "[$timestamp] $message" -Encoding UTF8
}

function Save-State([string]$status, [string]$errorMessage = '') {
  $payload = @{
    status = $status
    target_version = $targetVersion
    install_dir = $installDir
    log_path = $logPath
    error = $errorMessage
    updated_at = (Get-Date).ToString('s')
  } | ConvertTo-Json -Depth 5
  Set-Content -LiteralPath $statePath -Value $payload -Encoding UTF8
}

try {
  Set-Location -LiteralPath ([System.IO.Path]::GetTempPath())

  if (Test-Path -LiteralPath $logPath) {
    Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue
  }
  Save-State -status 'pending'

  Write-Log 'Inicio de parche portable.'
  Write-Log "ZIP: $zipPath"
  Write-Log "InstallDir: $installDir"
  Write-Log "PID actual: $currentPid"
  Write-Log "Version objetivo: $targetVersion"

  for ($i = 0; $i -lt 120; $i++) {
    $proc = Get-Process -Id $currentPid -ErrorAction SilentlyContinue
    if (-not $proc) {
      Write-Log 'Proceso principal liberado.'
      break
    }
    Start-Sleep -Milliseconds 500
  }

  if (Get-Process -Id $currentPid -ErrorAction SilentlyContinue) {
    throw "La aplicación principal no se cerró a tiempo. PID: $currentPid"
  }

  if (Test-Path -LiteralPath $extractDir) {
    Write-Log 'Limpiando extractDir anterior.'
    Remove-Item -LiteralPath $extractDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  if (Test-Path -LiteralPath $stagingDir) {
    Write-Log 'Limpiando stagingDir anterior.'
    Remove-Item -LiteralPath $stagingDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

  Write-Log 'Expandiendo ZIP portable.'
  Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

  $packageDir = Join-Path $extractDir 'ExelciorApolo'
  if (-not (Test-Path -LiteralPath $packageDir)) {
    $dirs = @(Get-ChildItem -LiteralPath $extractDir -Directory)
    if ($dirs.Count -eq 1) {
      $packageDir = $dirs[0].FullName
    }
  }
  if (-not (Test-Path -LiteralPath $packageDir)) {
    throw 'No se encontró la carpeta ExelciorApolo dentro del paquete portable.'
  }

  Write-Log 'Copiando paquete expandido a staging.'
  Copy-Item -LiteralPath $packageDir -Destination $stagingDir -Recurse -Force
  $newExe = Join-Path $stagingDir $exeName
  if (-not (Test-Path -LiteralPath $newExe)) {
    throw "No se encontró el ejecutable esperado en el paquete: $newExe"
  }
  Write-Log "Ejecutable validado en staging: $newExe"

  if (Test-Path -LiteralPath $backupDir) {
    Write-Log 'Eliminando backup anterior.'
    Remove-Item -LiteralPath $backupDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  if (Test-Path -LiteralPath $installDir) {
    Write-Log 'Moviendo instalación actual a backup.'
    Move-Item -LiteralPath $installDir -Destination $backupDir -Force
  }
  Write-Log 'Moviendo staging a instalación final.'
  Move-Item -LiteralPath $stagingDir -Destination $installDir -Force

  $targetExe = Join-Path $installDir $exeName
  if (-not (Test-Path -LiteralPath $targetExe)) {
    if (Test-Path -LiteralPath $installDir) {
      Remove-Item -LiteralPath $installDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $backupDir) {
      Move-Item -LiteralPath $backupDir -Destination $installDir -Force
    }
    throw "La actualización no dejó un ejecutable válido en: $targetExe"
  }
  Write-Log "Instalación final válida: $targetExe"

  $desktopDir = [Environment]::GetFolderPath('Desktop')
  if ($desktopDir -and (Test-Path -LiteralPath $desktopDir)) {
    Write-Log 'Recreando acceso directo de escritorio.'
    foreach ($shortcutName in $desktopNames) {
      $shortcutPath = Join-Path $desktopDir $shortcutName
      if (Test-Path -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force -ErrorAction SilentlyContinue
      }
    }

    $shortcutPath = Join-Path $desktopDir $desktopNames[0]
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $targetExe
    $Shortcut.WorkingDirectory = $installDir
    $Shortcut.IconLocation = "$targetExe,0"
    $Shortcut.Save()
  }

  if (Test-Path -LiteralPath $backupDir) {
    Write-Log 'Eliminando backup antiguo.'
    Remove-Item -LiteralPath $backupDir -Recurse -Force -ErrorAction SilentlyContinue
  }

  Write-Log 'Relanzando ejecutable actualizado.'
  Save-State -status 'applied'
  Start-Process -FilePath $targetExe -WorkingDirectory $installDir
} catch {
  Write-Log "Fallo de parche portable: $($_.Exception.Message)"
  Save-State -status 'failed' -errorMessage $_.Exception.Message
  throw
}
