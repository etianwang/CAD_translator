; Honsen DrawTranslate — Inno Setup 安装脚本
; 源文件目录：E:\Project\Honsen DrawTranslate
; 用 Inno Setup Compiler 打开本脚本并编译即可生成安装包

#define MyAppName "Honsen CAD Translator"
#define MyAppVersion "1.9.5"
#define MyAppPublisher "Honsen-Etienne"
#define MyAppExeName "Honsen DrawTranslate v1.9.5.exe"
#define MyAppURL "https://github.com/etianwang/CAD_translator"

[Setup]
AppId={{A7B3C9E1-4D2F-4A8B-9C1E-6F5D8A2B3C4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Honsen DrawTranslate
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; 安装包输出到本目录下的 Output 文件夹
OutputDir=Output
OutputBaseFilename=Honsen_DrawTranslate_v{#MyAppVersion}_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
DisableProgramGroupPage=no
VersionInfoVersion={#MyAppVersion}.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
; 显示“准备安装”页，便于确认路径与快捷方式选项
DisableReadyPage=no
DisableDirPage=no
UsePreviousAppDir=no
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"; Flags: checkedonce

[Files]
; 主程序
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; ODA File Converter 及依赖（完整子目录）
Source: "..\dist\ODAFileConverter\*"; DestDir: "{app}\ODAFileConverter"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
; 桌面快捷方式（由 Tasks 控制）
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Must run during /VERYSILENT updates too; start unelevated when Setup used UAC.
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait runasoriginaluser

[UninstallDelete]
; 卸载时清理可能产生的运行时缓存（如有）
Type: filesandordirs; Name: "{app}"
