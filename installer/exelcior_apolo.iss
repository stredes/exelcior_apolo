#define AppName "Exelcior Apolo"
#define AppVersion "1.4.0"
#define AppPublisher "AMILAB / Exelcior"
#define AppExeName "ExelciorApolo.exe"

[Setup]
AppId={{b25fd1fa-3a48-410e-ad0a-94e099694a77}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Instala en Program Files correcto según bitness del instalador
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}

; Rutas RELATIVAS al propio .iss (carpeta installer)
LicenseFile={#SourcePath}\LICENSE.txt
OutputDir={#SourcePath}\output
OutputBaseFilename=ExelciorApolo_{#AppVersion}_Setup

Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; Si tu app es solo x64, deja estas dos líneas. 
; Si quieres permitir x86, bórralas.
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; El dist está un nivel arriba del .iss
Source: "..\dist\ExelciorApolo\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Flags: nowait postinstall skipifsilent
