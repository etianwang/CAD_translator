; Honsen CAD 中法英互译 — Inno Setup 安装脚本
; 构建前请先运行 PyInstaller，并将 ODA（可选）放入 dist\ODAFileConverter\

#define MyAppName "Honsen CAD 中法英互译"
#define MyAppVersion "1.7.0"
#define MyAppPublisher "Honsen"
#define MyAppExeName "Honsen_CAD_Translator_v1.7.0.exe"
#define MyAppURL "https://github.com/"

[Setup]
AppId={{8F3A2C1D-9B4E-4F6A-A1D2-3E5F7C8B9A0D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Honsen CAD Translator
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=Honsen_CAD_Translator_v{#MyAppVersion}_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
LicenseFile=
InfoBeforeFile=
VersionInfoVersion={#MyAppVersion}.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"; Flags: unchecked

[Files]
; 主程序（PyInstaller onefile）
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; ODA File Converter（与主程序同级；打包前放入 dist\ODAFileConverter\）
Source: "..\dist\ODAFileConverter\*"; DestDir: "{app}\ODAFileConverter"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function OdaBundled: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\ODAFileConverter\ODAFileConverter.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not OdaBundled then
      MsgBox(
        '安装完成。' + #13#10 + #13#10 +
        '未检测到 ODA File Converter，当前仅可直接翻译 DXF 文件。' + #13#10 +
        '如需 DWG 支持，请将 ODA 完整文件复制到：' + #13#10 +
        ExpandConstant('{app}\ODAFileConverter\') + #13#10 + #13#10 +
        '或在 AutoCAD 中将 DWG 另存为 DXF 后翻译。',
        mbInformation, MB_OK);
  end;
end;
