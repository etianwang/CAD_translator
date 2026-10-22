; Honsen DrawTranslate — Inno Setup 安装脚本
; 源文件目录：E:\Project\Honsen DrawTranslate
; 用 Inno Setup Compiler 打开本脚本并编译即可生成安装包

#define MyAppName "Honsen CAD Translator"
#define MyAppVersion "1.11.11"
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
VersionInfoVersion={#MyAppVersion}.0
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
; 不按通配符删除历史 EXE；未知文件默认保留。
; 清理由本安装器旧版本创建的默认英文快捷方式；不扫描用户其他链接。
Type: files; Name: "{autodesktop}\Honsen CAD Translator.lnk"
Type: files; Name: "{autoprograms}\Honsen CAD Translator\Honsen CAD Translator.lnk"
Type: files; Name: "{autoprograms}\Honsen CAD Translator\卸载 Honsen CAD Translator.lnk"
Type: dirifempty; Name: "{autoprograms}\Honsen CAD Translator"

[Icons]
; 开始菜单
Name: "{group}\{#MyShortcutName}"; Filename: "{app}\HonsenUpdateRunner.exe"; Parameters: "launch --app-id {#MyHonsenAppId} --source app"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyShortcutName}"; Filename: "{uninstallexe}"
; 桌面快捷方式（由 Tasks 控制）
Name: "{autodesktop}\{#MyShortcutName}"; Filename: "{app}\HonsenUpdateRunner.exe"; Parameters: "launch --app-id {#MyHonsenAppId} --source app"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Honsen Program unified application identity. This installer is per-machine
; (PrivilegesRequired=admin), so the shared HKLM location is authoritative.
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "AppId"; ValueData: "{#MyHonsenAppId}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"
Root: HKLM; Subkey: "Software\Honsen Program\Apps\{#MyHonsenAppId}"; ValueType: string; ValueName: "InstallScope"; ValueData: "machine"
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
  ExistingRegistrationError: String;
  ExistingIsDamaged: Boolean;

procedure CheckExistingRegistration(RootKey: Integer; MachineNative: Boolean);
var
  Location, AppId, ExecutablePath, Scope: String;
begin
  if not RegKeyExists(RootKey, 'Software\Honsen Program\Apps\{#MyHonsenAppId}') then
    exit;
  if not RegQueryStringValue(RootKey, 'Software\Honsen Program\Apps\{#MyHonsenAppId}', 'InstallLocation', Location) or (Location = '') then begin
    ExistingRegistrationError := '发现损坏登记，缺少安装目录；请先人工修复登记。';
    exit;
  end;
  if (ExtractFileDrive(Location) = '') or (CompareText(RemoveBackslashUnlessRoot(Location), RemoveBackslashUnlessRoot(ExpandFileName(Location))) <> 0) then begin
    ExistingRegistrationError := '安装登记的目录不是规范绝对路径。';
    exit;
  end;
  if (ExistingInstallLocation <> '') and (CompareText(RemoveBackslashUnlessRoot(Location), RemoveBackslashUnlessRoot(ExistingInstallLocation)) <> 0) then begin
    ExistingRegistrationError := '发现冲突安装目录，请先人工处理：' + Location;
    exit;
  end;
  ExistingInstallLocation := Location;
  if not MachineNative then begin
    ExistingRegistrationError := '发现用户或其他注册表视图中的登记；本安装器仅支持全机安装，请先人工处理：' + Location;
    exit;
  end;
  if not RegQueryStringValue(RootKey, 'Software\Honsen Program\Apps\{#MyHonsenAppId}', 'AppId', AppId) or (AppId <> '{#MyHonsenAppId}') then
    ExistingRegistrationError := '安装登记的 AppId 无效。';
  if RegQueryStringValue(RootKey, 'Software\Honsen Program\Apps\{#MyHonsenAppId}', 'InstallScope', Scope) and (Scope <> 'machine') then
    ExistingRegistrationError := '安装范围与全机登记不一致。';
  if not RegQueryStringValue(RootKey, 'Software\Honsen Program\Apps\{#MyHonsenAppId}', 'ExecutablePath', ExecutablePath) or
     (CompareText(ExecutablePath, AddBackslash(Location) + '{#MyAppExeName}') <> 0) then begin
    ExistingRegistrationError := '登记的主程序路径与安装目录不一致。';
    exit;
  end;
  ExistingIsDamaged := not FileExists(ExecutablePath);
end;

function ReadExistingInstallLocation(): String;
begin
  ExistingInstallLocation := '';
  ExistingRegistrationError := '';
  ExistingIsDamaged := False;
  CheckExistingRegistration(HKLM32, not IsWin64);
  if IsWin64 then CheckExistingRegistration(HKLM64, True);
  CheckExistingRegistration(HKCU32, False);
  if IsWin64 then CheckExistingRegistration(HKCU64, False);
  Result := ExistingInstallLocation;
end;

procedure InitializeWizard();
begin
  ExistingInstallLocation := ReadExistingInstallLocation();
  if ExistingInstallLocation <> '' then begin
    WizardForm.DirEdit.Text := ExistingInstallLocation;
    if (ExistingRegistrationError = '') and ExistingIsDamaged and not WizardSilent then
      MsgBox('检测到损坏安装，修复只能使用原目录：' + ExistingInstallLocation, mbInformation, MB_OK);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  ReadExistingInstallLocation();
  Result := ExistingRegistrationError;
  if (Result = '') and (ExistingInstallLocation <> '') and (CompareText(RemoveBackslashUnlessRoot(WizardDirValue), RemoveBackslashUnlessRoot(ExistingInstallLocation)) <> 0) then
    Result := '已安装的 Honsen CAD Translator 只能更新原目录：' + ExistingInstallLocation;
end;

[Run]
; Manual installs may offer launch. Silent updates are restarted only by HonsenUpdateRunner.
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait runasoriginaluser postinstall
