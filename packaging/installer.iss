; DeveloperOS Windows installer (desktop ladder step D, D-0032).
; Build: ./build_installer.ps1  (or: iscc /DMyAppVersion=x.y.z installer.iss)
;
; Design (D-0032):
; - PER-USER install (PrivilegesRequired=lowest): no admin/UAC, lands in
;   {localappdata}\Programs\DeveloperOS - right for a single-user local tool.
; - KEEP-USER-DATA: the uninstaller removes ONLY what the installer placed.
;   The user's workspace (%APPDATA%\DeveloperOS: SQLite DB, settings.json)
;   is deliberately never touched, so uninstall/reinstall never loses work.
; - Updates are MANUAL by design (no auto-update code, no network surface):
;   download a newer Setup from the GitHub Releases page and run it - it
;   upgrades in place (same AppId).

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

[Setup]
AppId={{6D573026-4BA8-4D68-A64F-EE37FD2CD570}
AppName=DeveloperOS
AppVersion={#MyAppVersion}
AppVerName=DeveloperOS {#MyAppVersion}
AppPublisher=DeveloperOS (open source, MIT)
AppPublisherURL=https://github.com/taysh123/DeveloperOS
AppSupportURL=https://github.com/taysh123/DeveloperOS/issues
AppUpdatesURL=https://github.com/taysh123/DeveloperOS/releases
DefaultDirName={autopf}\DeveloperOS
DefaultGroupName=DeveloperOS
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
SetupIconFile=devos.ico
UninstallDisplayIcon={app}\DeveloperOS.exe
OutputDir=dist
OutputBaseFilename=DeveloperOS-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\DeveloperOS.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\DeveloperOS"; Filename: "{app}\DeveloperOS.exe"; Comment: "Your private, local-first developer workspace"
Name: "{autodesktop}\DeveloperOS"; Filename: "{app}\DeveloperOS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DeveloperOS.exe"; Description: "Launch DeveloperOS now"; Flags: nowait postinstall skipifsilent

; KEEP-USER-DATA: no [UninstallDelete] section on purpose - the user's
; workspace under %APPDATA%\DeveloperOS survives uninstall by design.
