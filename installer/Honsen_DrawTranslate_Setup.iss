; Honsen DrawTranslate — Inno Setup 安装脚本
; 源文件目录：E:\Project\Honsen DrawTranslate
; 用 Inno Setup Compiler 打开本脚本并编译即可生成安装包

#define MyAppName "Honsen CAD Translator"
#define MyAppVersion "1.11.8"
#define MyAppPublisher "Honsen"
#define MyAppExeName "Honsen DrawTranslate.exe"
#define MyShortcutName "Honsen CAD 翻译器"
#define MyAppURL "https://github.com/etianwang/CAD_translator"
#define MyHonsenAppId "honsen.cad-translator"
#define MyHonsenUpdateURL "https://api.github.com/repos/etianwang/CAD_translator/releases/latest"

[Setup]
AppId={{A7B3C9E1-4D2F-4A8B-9C1E-6F5D8A2B3C4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Honsen Program\Honsen DrawTranslate
DefaultGroupName={#MyShortcutName}
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
UsePreviousAppDir=yes
UsePreviousGroup=no
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"; Flags: checkedonce

[Files]
; 主程序
Source: "..\dist\Honsen DrawTranslate.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\HonsenUpdateRunner.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\honsen.app.json"; DestDir: "{app}"; Flags: ignoreversion
; ODA File Converter 及依赖（完整子目录）
Source: "..\dist\ODAFileConverter\*"; DestDir: "{app}\ODAFileConverter"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; 只删除本产品历史版本的 EXE；绝不使用宽泛的 {app}\*.exe 通配符。
Type: files; Name: "{app}\Honsen DrawTranslate v*.exe"
Type: files; Name: "{app}\Honsen_CAD_Translator_v*.exe"
; 清理由本安装器旧版本创建的默认英文快捷方式；不扫描用户其他链接。
Type: files; Name: "{autodesktop}\Honsen CAD Translator.lnk"
Type: files; Name: "{autoprograms}\Honsen CAD Translator\Honsen CAD Translator.lnk"
Type: files; Name: "{autoprograms}\Honsen CAD Translator\卸载 Honsen CAD Translator.lnk"
Type: dirifempty; Name: "{autoprograms}\Honsen CAD Translator"

[Icons]
; 开始菜单
Name: "{group}\{#MyShortcutName}"; Filename: "{app}\HonsenUpdateRunner.exe"; Parameters: "launch"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyShortcutName}"; Filename: "{uninstallexe}"
; 桌面快捷方式（由 Tasks 控制）
Name: "{autodesktop}\{#MyShortcutName}"; Filename: "{app}\HonsenUpdateRunner.exe"; Parameters: "launch"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Honsen Program unified application identity. This installer is per-machine
; (PrivilegesRequired=admin), so the shared HKLM location is authoritative.
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "AppId"; ValueData: "{#MyHonsenAppId}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "InstallLocation"; ValueData: "{app}"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "ExecutablePath"; ValueData: "{app}\{#MyAppExeName}"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "UpdateRunnerPath"; ValueData: "{app}\HonsenUpdateRunner.exe"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "LauncherPath"; ValueData: "{app}\HonsenUpdateRunner.exe"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "UpdateManifestUrl"; ValueData: "{#MyHonsenUpdateURL}"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "UpdateUrl"; ValueData: "{#MyHonsenUpdateURL}"

[Code]
var
  ExistingInstallLocation: String;

function ReadExistingInstallLocation(): String;
begin
  Result := '';
  if not RegQueryStringValue(HKLM, 'Software\Honsen Program\Apps\{#MyHonsenAppId}', 'InstallLocation', Result) then
    RegQueryStringValue(HKCU, 'Software\Honsen Program\Apps\{#MyHonsenAppId}', 'InstallLocation', Result);
end;

procedure InitializeWizard();
begin
  ExistingInstallLocation := ReadExistingInstallLocation();
  if ExistingInstallLocation <> '' then
    WizardForm.DirEdit.Text := ExistingInstallLocation;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if (ExistingInstallLocation <> '') and (CompareText(RemoveBackslashUnlessRoot(WizardDirValue), RemoveBackslashUnlessRoot(ExistingInstallLocation)) <> 0) then
    Result := '已安装的 Honsen CAD Translator 只能更新原目录：' + ExistingInstallLocation;
end;

[Run]
; Manual installs may offer launch. Silent updates are restarted only by HonsenUpdateRunner.
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait runasoriginaluser postinstall

[UninstallDelete]
; 卸载时清理可能产生的运行时缓存（如有）
Type: filesandordirs; Name: "{app}"
