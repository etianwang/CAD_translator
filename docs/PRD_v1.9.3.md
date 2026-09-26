# v1.9.3 PRD：安全自动更新

## 目标

Windows 桌面版在启动时静默检查稳定版 GitHub Release；用户确认后下载并校验安装包，关闭当前应用后完成安装并重启。

## 范围

- 固定检查 `etianwang/CAD_translator` 的 GitHub `releases/latest`，只接受比内置版本号更新的稳定版。
- 只接受名为 `HonsenCAD.vX.Y.Z.exe` 或 `Honsen_DrawTranslate_vX.Y.Z_Setup.exe`，且 GitHub API 提供 `sha256:` digest 的 Windows 安装包；下载完成后必须比对 SHA-256。
- 启动时不打断用户；发现新版才显示更新窗口。标题栏提供“检查更新”。
- 点击“立即更新”后下载、校验、启动 Inno Setup 静默安装包，再退出当前桌面程序；安装包负责替换 EXE、ODA 目录与重启。
- 更新检查与下载不受授权状态阻塞，保证过期客户端仍可获得安全修复。

## 非目标

- 不下载或覆盖正在运行的 EXE；不接受无 digest 的资产。
- 不自动发布 GitHub Release，也不处理 macOS DMG 的就地安装。
- 不新增第三方依赖、不复用许可证密钥作为更新签名。

## 发布规则

每个 Windows Release 必须上传 Inno Setup 输出的 `HonsenCAD.vX.Y.Z.exe`（现行命名）或 `Honsen_DrawTranslate_vX.Y.Z_Setup.exe`。GitHub Release API 的该资产 `digest` 是客户端传输完整性校验依据；缺少规范资产或 digest 时，客户端拒绝自动安装并显示原因。

## 验收标准

1. 当前版本或网络失败时，检查结果不会阻塞主界面。
2. 仅在 Release 版本大于当前版本、文件名与版本一致且存在 SHA-256 digest 时，显示“立即更新”。
3. 下载内容与 digest 不一致时删除临时文件并拒绝安装。
4. Windows 只启动已经校验的 Inno Setup 包，再退出当前程序；静默安装结束后必须以启动安装器的原用户身份自动打开新版本；非 Windows 不提供自动安装。
