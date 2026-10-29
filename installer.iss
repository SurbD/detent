; Inno Setup 6 script  ->  Output\Detent-Setup.exe
; Packs the folder build from build.bat (dist\Detent\), which starts much faster at login than a one-file exe.
; Code signing (strongly recommended): add  SignTool=signtool  and define it in the Inno IDE / ISCC /S switch.
[Setup]
AppName=Detent
AppVersion=1.3.0
AppPublisher=Guyde
DefaultDirName={autopf}\Detent
DefaultGroupName=Detent
OutputBaseFilename=Detent-Setup
SetupIconFile=detent.ico
UninstallDisplayIcon={app}\Detent.exe
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
; ask the user to quit a running Detent before files are replaced
AppMutex=Local\DetentSingleInstance
CloseApplications=yes

[InstallDelete]
; clear the previous version's libraries so old files never mix with new ones
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\Detent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Detent"; Filename: "{app}\Detent.exe"
Name: "{userdesktop}\Detent"; Filename: "{app}\Detent.exe"; Tasks: desktopicon

[Tasks]
Name: "startup"; Description: "Start Detent with Windows (recommended)"
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Registry]
; Start with Windows: written or removed according to the checkbox above
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Detent"; ValueData: """{app}\Detent.exe"""; Tasks: startup
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "Detent"; Flags: deletevalue; Tasks: not startup
; always remove the startup entry on uninstall
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "Detent"; Flags: uninsdeletevalue dontcreatekey
; hand the choice to the app: it reads this once on next launch and updates its own setting to match
Root: HKCU; Subkey: "Software\Detent"; ValueType: dword; ValueName: "StartWithWindows"; ValueData: 1; Flags: uninsdeletekey; Tasks: startup
Root: HKCU; Subkey: "Software\Detent"; ValueType: dword; ValueName: "StartWithWindows"; ValueData: 0; Flags: uninsdeletekey; Tasks: not startup

[Run]
Filename: "{app}\Detent.exe"; Description: "Start Detent now"; Flags: nowait postinstall skipifsilent
