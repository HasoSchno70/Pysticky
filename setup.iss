; Inno Setup Script fuer PySticky.
; Baut aus dem PyInstaller-Onefile-Build (dist\PySticky.exe) einen
; Windows-Installer mit Start-Menu-Eintrag, optionalem Desktop-Icon und
; Deinstallations-Routine -- Alternative zum rohen .exe-Download, den
; Windows SmartScreen ansonsten pauschal als "unbekannter Herausgeber"
; markiert (das aendert ein Installer allein NICHT, das ist eine reine
; Code-Signing/Reputations-Frage).
;
; Aufruf (siehe .github/workflows/ci.yml):
;   ISCC.exe /DMyAppVersion=1.2.3 setup.iss
; MyAppVersion faellt lokal ohne /D-Parameter auf "0.0.0" zurueck, damit
; das Script auch manuell testbar bleibt.

#define MyAppName "PySticky"
#define MyAppPublisher "Hans Schnorrenberger"
#define MyAppExeName "PySticky.exe"
#define MyAppURL "https://github.com/HasoSchno70/Pysticky"

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
; Feste AppId (NICHT aendern) -- Windows erkennt darueber Updates auf
; dieselbe Installation statt jede Version als neues Programm zu fuehren.
AppId={{F38324D1-15BE-450B-A677-5DCAD5213DC7}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename=PySticky-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
; sticken.ico ist bewusst NICHT hier verwendet: Inno Setups Resource-Patcher
; scheitert an dessen einzelnem 1024x1024-Frame ("File is too large"). Diese
; kleinere Multi-Groessen-Variante (16-256px) ist nur fuers Installer-Icon.
SetupIconFile=src\pysticky\resources\icons\sticken_installer.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\PySticky.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
