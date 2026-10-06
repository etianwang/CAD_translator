# CAD 翻译器更新、工具箱与发布强制契约

> **强制阅读。** 任何新 agent、新对话、发布者或工具箱接入者，在执行任何任务前必须先阅读本文件、`docs/MEMORY.md`，再按任务读取相关文档。除非用户明确修改本契约，否则不得另行设计更新、安装、启动、结果回传或发布方式。

本文件是 Honsen CAD 翻译器 Windows 更新、Honsen 工具箱联动和发布流程的唯一规范。当前已由 **v1.11.8** 验证为工具箱首个正式接入应用。

## 固定身份与唯一职责

| 项目 | 固定值 |
| --- | --- |
| appId | `honsen.cad-translator` |
| 主程序 | `Honsen DrawTranslate.exe` |
| 唯一更新执行器 | `HonsenUpdateRunner.exe` |
| 发布者 | `Honsen` |
| 当前自动更新源 | GitHub stable Release |

只有 `HonsenUpdateRunner.exe` 可以等待或终止主程序、启动 Inno、覆盖已安装文件、验证安装结果、重启应用和写最终结果。

主程序与工具箱可以下载更新包，但必须在调用 Runner 前校验 SHA-256；它们绝不能直接启动 Inno、覆盖、移动、删除或迁移应用文件。

## 发现与身份契约

应用的唯一注册表键为：

```text
HKLM\Software\Honsen Program\Apps\honsen.cad-translator
```

当前用户安装才使用同路径 HKCU 键；同一台机器不得同时存在不同目录的同 appId 安装。

该键必须包含且与 manifest 一致：

```text
AppId = honsen.cad-translator
Version
Publisher = Honsen
InstallLocation
ExecutablePath
LauncherPath
UpdateRunnerPath
UpdateManifestUrl
```

工具箱只能通过精确 appId 读取该键。禁止按显示名、快捷方式、固定目录或磁盘扫描推测安装位置。

`<InstallLocation>\honsen.app.json` 必须包含：

```json
{
  "schemaVersion": 1,
  "appId": "honsen.cad-translator",
  "displayName": "Honsen CAD 翻译器",
  "version": "X.Y.Z",
  "executable": "Honsen DrawTranslate.exe",
  "updateRunner": "HonsenUpdateRunner.exe",
  "publisher": "Honsen",
  "updateManifestUrl": "https://api.github.com/repos/etianwang/CAD_translator/releases/latest"
}
```

`executableName` 与 `updateRunnerName` 仅作为历史兼容字段保留；所有新代码优先使用标准字段。Runner 必须验证 appId、Publisher、UpdateManifestUrl、安装目录、主程序和 Runner 路径均与注册表一致。

## 统一入口

桌面/开始菜单快捷方式与工具箱“打开”统一调用：

```text
<LauncherPath> launch --source toolbox --operation-id <GUID> --result-path <绝对结果路径>
```

工具箱“更新”在下载并验证 SHA-256 后统一调用：

```text
<UpdateRunnerPath> apply
  --source toolbox
  --app-id honsen.cad-translator
  --wait-pid <主程序 PID；未运行为 0>
  --installer <已校验安装包绝对路径>
  --sha256 <SHA-256>
  --target-dir <注册表 InstallLocation>
  --expected-version <目标版本>
  --restart false
  --operation-id <GUID>
  --result-path "%LOCALAPPDATA%\Honsen Program\UpdateResults\honsen.cad-translator\<GUID>.json"
```

主程序将自身已验证的下载包交给 Runner 时使用同一 `apply`，但传入自身 PID、实际运行目录和 `--restart true`。主程序不得依赖应用名称推断目录，也不得保留直接 Inno 更新兜底。

## Runner 不可变安全流程

```text
验证注册表 + manifest + 参数
→ 将 Runner 复制到 %TEMP%\Honsen Program\UpdateRunner\<GUID>\
→ 获取 appId 命名互斥锁
→ 校验安装包 SHA-256
→ 等待目标 PID 退出
→ UAC 静默运行 Inno，且只覆盖 InstallLocation
→ 检查退出码、日志、注册表、manifest、exe 文件版本
→ 原子写入本 operation 的结果 JSON
→ 仅 restart=true 时启动注册表 ExecutablePath
```

- PID 先等待 30 秒；仅当 PID 的实际 exe 路径严格等于 `ExecutablePath` 时才可结束，之后必须确认退出。
- 同 appId 出现不同 `InstallLocation`、路径不一致、Publisher/更新源不一致、SHA-256 不一致或安装验证失败，必须立即失败。
- Inno 参数固定为：

```text
/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
/DIR="<InstallLocation>"
/LOG="<operation-scoped .inno.log>"
```

- 绝不创建第二份安装、迁移目录、扫描磁盘或覆盖共享父目录。

Runner 为无控制台程序，使用一个原生进度窗口显示检查、下载、等待、安装、验证和启动。发现更新时，同一窗口内提供“立即更新 / 稍后提醒 / 跳过此版本”；不得弹出第二个系统确认框。

## 操作级结果契约

每次入口都生成一个 GUID，并且只能读取自己传入的结果文件：

```text
%LOCALAPPDATA%\Honsen Program\UpdateResults\honsen.cad-translator\<operationId>.json
```

固定字段：

```json
{
  "appId": "honsen.cad-translator",
  "status": "success | failed",
  "source": "app | toolbox",
  "operationId": "GUID",
  "fromVersion": "... | null",
  "toVersion": "... | null",
  "step": "... | null",
  "installerExitCode": "number | null",
  "installerLogPath": "... | null",
  "message": "... | null",
  "completedAtUtc": "UTC ISO-8601"
}
```

不得恢复共享的 `<appId>.json`、`failureStep`、`logPath` 或 `error` 字段。工具箱不得以进程启动成功、安装包存在或共享旧结果判断更新成功。

## 安装、卸载与快捷方式

- 首次安装可选目录；同 appId 已安装时只能更新原 `InstallLocation`。
- 标准快捷方式目标始终为 `HonsenUpdateRunner.exe launch`，图标明确引用 `Honsen DrawTranslate.exe`。
- 静默安装不得自行重启；成功重启只由 Runner 完成。
- 卸载只能删除应用 `{app}` 和 `honsen.cad-translator` 专属注册表键；绝不删除共享 `Honsen Program` 父目录、其他 Honsen 应用或其数据。

## 发布强制流程

发布远端固定如下；`origin` 与 `gitee` 都是每次源代码和版本标签发布的必达远端：

| 远端 | 固定地址 |
| --- | --- |
| GitHub `origin` | `https://github.com/etianwang/CAD_translator.git` |
| Gitee `gitee` | `https://gitee.com/etianwang/CAD-translator.git` |

任何 `main` 或 `vX.Y.Z` 标签推送都必须同时到达两个远端。任一推送失败时，必须修复并重试，不能宣布发布完成。当前 Runner 自动更新源仍只使用 GitHub Release；Gitee 仓库镜像不改变该更新源。

1. 严格递增 `X.Y.Z`，同步版本到后端、桌面标题、前端、`honsen.app.json`、Windows 版本资源、Inno、安装包名称及测试夹具。
2. 运行：

   ```powershell
   python -m unittest tests.test_updater
   python -m compileall -q backend desktop run.py
   Push-Location frontend; npm run build; Pop-Location
   .\installer\build_installer.ps1
   git diff --check
   ```

3. 确认主 exe 文件版本、安装包存在并计算 SHA-256；二进制不得提交 Git。
4. 提交源代码，创建带注释 `vX.Y.Z` 标签，并执行：

   ```powershell
   git push origin main
   git push gitee main
   git push origin vX.Y.Z
   git push gitee vX.Y.Z
   ```

   四次推送均成功才可进入 Release 步骤。
5. GitHub 创建公开、非 draft、非 prerelease Release，上传 `Honsen_DrawTranslate_vX.Y.Z_Setup.exe`；核对 GitHub `sha256:` asset digest 与本地摘要完全一致。
6. Release 说明使用真实 Markdown 换行，不能传入字面量 `\n`。Gitee 作为仓库/标签/Release 镜像；当前 Runner 的自动更新源仍只能是 GitHub Release。
7. 在 `docs/MEMORY.md` 写入版本、提交、标签、Release URL、文件大小、SHA-256、验证项与未执行 E2E；记录后再提交推送。

## 修改本契约的门槛

任何涉及 Runner、manifest、注册表、工具箱调用、结果 JSON、安装器、卸载或发布的变更，必须：

1. 先更新本文件和对应详细协议文档；
2. 更新或新增最小回归测试；
3. 完成构建与相关验证；
4. 在 `docs/MEMORY.md` 记录决策、验证结果和迁移影响。

相关细节见 [CURRENT_UPDATE_AND_TOOLBOX_INTEGRATION.md](CURRENT_UPDATE_AND_TOOLBOX_INTEGRATION.md)、[HONSEN_UPDATE_RUNNER.md](HONSEN_UPDATE_RUNNER.md)、[RELEASE_AND_AUTO_UPDATE.md](RELEASE_AND_AUTO_UPDATE.md) 和 [TEST_RULES.md](TEST_RULES.md)；本文件优先级最高。
