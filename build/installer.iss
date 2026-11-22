; NEX 视频增强 — Inno Setup 安装脚本
; 编译：ISCC.exe build\installer.iss

#define MyAppName "NEX 视频增强"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "NEX"
#define MyAppExeName "NEX.exe"

[Setup]
AppId={{6E1F4C2A-9D3B-4A8E-B5C7-2F1D8A6E4C90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\NEX
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=NEX_Setup_{#MyAppVersion}
SetupIconFile=..\nex\resources\nex.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=lowest
SetupLogging=yes
CloseApplications=yes
VersionInfoVersion=0.1.0.0
VersionInfoCompany=NEX
VersionInfoDescription=NEX 视频增强 安装程序

[Languages]
Name: "chinesesimplified"; MessagesFile: "languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\NEX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\engines\ffmpeg\*"; DestDir: "{app}\engines\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\engines\realesrgan\*"; DestDir: "{app}\engines\realesrgan"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\engines\rife\rife-ncnn-vulkan.exe"; DestDir: "{app}\engines\rife"; Flags: ignoreversion
Source: "..\engines\rife\vcomp140.dll"; DestDir: "{app}\engines\rife"; Flags: ignoreversion
Source: "..\engines\rife\LICENSE"; DestDir: "{app}\engines\rife"; Flags: ignoreversion
Source: "..\engines\rife\README.md"; DestDir: "{app}\engines\rife"; Flags: ignoreversion
Source: "..\engines\rife\rife-v4.6\*"; DestDir: "{app}\engines\rife\rife-v4.6"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\engines\rife\rife-anime\*"; DestDir: "{app}\engines\rife\rife-anime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\engines\rife\rife-HD\*"; DestDir: "{app}\engines\rife\rife-HD"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\engines\rife\rife-UHD\*"; DestDir: "{app}\engines\rife\rife-UHD"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
