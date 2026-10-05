# Honsen Program 应用识别协议

Windows 安装包使用永久 appId `honsen.cad-translator`。发布后不得修改该值。

当前安装器是全电脑安装（`PrivilegesRequired=admin`），因此安装完成后写入：

```text
HKLM\Software\Honsen Program\Apps\honsen.cad-translator
```

安装目录中的 `honsen.app.json` 使用以下通用字段：

```json
{
  "schemaVersion": 1,
  "appId": "honsen.cad-translator",
  "displayName": "Honsen CAD 翻译器",
  "version": "X.Y.Z",
  "executable": "Honsen DrawTranslate.exe",
  "updateRunner": "HonsenUpdateRunner.exe",
  "publisher": "Honsen-Etienne",
  "updateManifestUrl": "https://api.github.com/repos/etianwang/CAD_translator/releases/latest"
}
```

CAD 暂时同时保留旧的 `executableName`、`updateRunnerName`，供已安装旧版 Runner/主程序兼容；新接入方只应依赖标准字段。

工具箱应只读取此精确键，不按名称模糊匹配，也不扫描可执行文件。键包含以下字符串值：

| 值名 | 含义 |
| --- | --- |
| `AppId` | 固定 appId：`honsen.cad-translator` |
| `DisplayName` | 用户可读名称 |
| `InstallLocation` | 安装目录 |
| `ExecutablePath` | 主程序完整路径 |
| `Version` | 已安装版本 |
| `UpdateUrl` | GitHub `releases/latest` API；与应用内更新检查使用同一稳定更新源 |

卸载时安装器删除整个专用 appId 键，因此该键的存在即表示该安装范围内的应用仍由安装器管理。若未来增加当前用户安装包，它必须改为写入同一相对路径的 `HKCU` 键，且不得同时写入 HKLM。
