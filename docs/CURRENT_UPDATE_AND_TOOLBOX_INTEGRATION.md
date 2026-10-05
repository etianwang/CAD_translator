# 当前更新逻辑与 Honsen 工具箱联动

本文记录 Honsen CAD 图纸中法英翻译器当前的 Windows 更新实现与工具箱集成契约。它描述的是已发布/已实现的行为；跨应用通用设计参考 [UPDATE_RUNNER_REFERENCE.md](UPDATE_RUNNER_REFERENCE.md)。

## 固定身份与责任边界

| 项目 | 值 |
| --- | --- |
| `appId` | `honsen.cad-translator` |
| 主程序 | `Honsen DrawTranslate.exe` |
| 唯一更新执行器 | `HonsenUpdateRunner.exe` |
| 安装描述文件 | `<InstallLocation>\honsen.app.json` |
| 更新结果 | `%LOCALAPPDATA%\Honsen Program\UpdateResults\honsen.cad-translator\<operationId>.json` |

`HonsenUpdateRunner.exe` 是唯一可以等待/结束主程序、启动 Inno、覆盖安装目录、验证安装结果、重启主程序并写入结果的组件。Runner 的 `launch` 可自行下载；主程序和工具箱也可下载，但必须先校验 SHA-256，且不得自行安装或替换文件。

主程序与 Honsen 工具箱都不得直接启动 Inno、移动/删除/覆盖应用文件，且不得自行猜测安装路径。

## 注册表契约

安装器写入以下其中一个键；当前全电脑安装默认使用 HKLM：

```text
HKLM\Software\Honsen Program\Apps\honsen.cad-translator
HKCU\Software\Honsen Program\Apps\honsen.cad-translator
```

| 值名 | 用途 |
| --- | --- |
| `AppId` | 必须为 `honsen.cad-translator` |
| `Version` | 当前已安装版本 |
| `InstallLocation` | 唯一允许被更新覆盖的目录 |
| `ExecutablePath` | 位于 `InstallLocation` 内的主程序绝对路径 |
| `LauncherPath` | Runner 的绝对路径；工具箱“打开”使用它 |
| `UpdateRunnerPath` | Runner 的绝对路径；工具箱“更新”使用它 |
| `UpdateManifestUrl` | 当前稳定更新源的 GitHub `releases/latest` API |
| `UpdateUrl` | 兼容字段，指向同一更新源 |

`honsen.app.json` 的标准字段为 `schemaVersion: 1`、`appId`、`displayName`、`version`、`executable`、`updateRunner`、`publisher`、`updateManifestUrl`。CAD 当前还保留 `executableName`、`updateRunnerName` 作为旧版本兼容字段；读取方必须优先使用标准字段。

工具箱必须按精确 `appId` 读取这个键。禁止通过显示名称、快捷方式、磁盘扫描或固定目录定位应用。

## 启动与自更新链路

桌面快捷方式、开始菜单快捷方式及工具箱“打开”统一执行：

```text
<LauncherPath> launch
```

Runner 的 `launch` 流程：

```text
读取并校验注册表 + honsen.app.json
→ 请求 UpdateManifestUrl（GitHub stable Release）
→ 无更高版本：启动 ExecutablePath
→ 有更高版本：展示版本、Release 说明与更新选项
→ 下载安装包、校验 GitHub 提供的 SHA-256
→ 调用同进程内 apply 流程
→ 验证成功后启动新主程序
```

更新提示的用户选择：

- **立即更新**：下载并安装，然后重启应用。
- **稍后提醒**：只启动当前版本；下次启动仍会提示。
- **跳过此版本**：只抑制该目标版本；偏好写入 `%LOCALAPPDATA%\Honsen Program\UpdatePreferences\honsen.cad-translator.json`。发布更高版本后必须重新提示。

Runner 是无控制台程序，但有原生进度窗口，显示检查、下载、等待退出、安装、验证与重启阶段；下载响应包含 `Content-Length` 时显示百分比。Inno 仍在后台静默运行。

## 主程序内的更新入口

主程序的本地桥接入口为 `NativeBridge.install_update(installer_path, sha256, expected_version)`。它只做以下工作：

1. 从自身真实运行目录读取 `honsen.app.json`，取得 `appId` 和 Runner 文件名。
2. 确认安装包、SHA-256、版本号和 Runner 都存在。
3. 启动同目录 Runner，并传入当前进程 PID 和真实安装目录。
4. 正常关闭主程序，使 Runner 能安全更新。

调用形态：

```text
HonsenUpdateRunner.exe apply
  --source app
  --app-id honsen.cad-translator
  --wait-pid <当前主程序 PID>
  --installer <已校验安装包绝对路径>
  --sha256 <SHA-256>
  --target-dir <主程序实际运行目录>
  --expected-version <目标版本>
  --restart true
  --operation-id <GUID>
  --result-path "%LOCALAPPDATA%\Honsen Program\UpdateResults\honsen.cad-translator\<GUID>.json"
```

主程序另有 `update_service_status()` 用于检测 Runner 是否存在；异常时应提示“更新服务异常，请通过 Honsen工具箱修复”。`restart_update_service()` 只在 Runner 存在时调用 `launch`，不会由主程序下载或替换自身文件。

## 工具箱联动

### 打开应用

工具箱读取 `LauncherPath` 后执行：

```powershell
$appId = 'honsen.cad-translator'
$key = "HKLM:\Software\Honsen Program\Apps\$appId"
$app = Get-ItemProperty $key
$operationId = [guid]::NewGuid().ToString()
$resultPath = Join-Path $env:LOCALAPPDATA "Honsen Program\UpdateResults\$appId\$operationId.json"
& $app.LauncherPath launch --source toolbox --operation-id $operationId --result-path $resultPath
```

工具箱不直接启动旧桌面快捷方式或硬编码的主 exe 路径。

### 发起更新

工具箱负责发现目标版本、下载安装包并校验 SHA-256；校验完成后只能调用 Runner：

```powershell
$appId = 'honsen.cad-translator'
$key = "HKLM:\Software\Honsen Program\Apps\$appId"
$app = Get-ItemProperty $key
$operationId = [guid]::NewGuid().ToString()
$resultPath = Join-Path $env:LOCALAPPDATA "Honsen Program\UpdateResults\$appId\$operationId.json"

& $app.UpdateRunnerPath apply `
  --source toolbox `
  --app-id $appId `
  --wait-pid <目标应用PID；未运行则 0> `
  --installer 'C:\Temp\Honsen_DrawTranslate_vX.Y.Z_Setup.exe' `
  --sha256 '<已校验的 SHA-256>' `
  --target-dir $app.InstallLocation `
  --expected-version 'X.Y.Z' `
  --restart false `
  --operation-id $operationId `
  --result-path $resultPath
```

工具箱等待 Runner 退出后读取结果文件，而不是根据进程启动成功或安装包存在来判断成功：

```text
%LOCALAPPDATA%\Honsen Program\UpdateResults\honsen.cad-translator\<operationId>.json
```

工具箱只能读取自己生成的 `$resultPath`，不得读取共享的“最新结果”。结果字段固定为 `appId`、`status`、`source`、`fromVersion`、`toVersion`、`step`、`installerExitCode`、`installerLogPath`、`message`、`completedAtUtc`，并附带 `operationId`。工具箱以 `--restart false` 更新时，成功后显示“更新完成，可打开”；如果确实需要自动打开，可以明确传 `--restart true`。

## Runner apply 的安全流程

```text
复制自身到 %TEMP%\Honsen Program\UpdateRunner\<GUID>\
→ 获取 Global\HonsenUpdate-honsen_cad-translator 互斥锁
→ 校验 appId、注册表、target-dir、manifest、主程序与 Runner 路径
→ 校验安装包 SHA-256
→ 等待目标 PID 退出
→ 以 UAC 启动 Inno 覆盖原目录
→ 校验退出码、日志、注册表、manifest 与 exe 文件版本
→ 原子写入结果 JSON
→ 按 restart 参数决定是否启动 ExecutablePath
```

关键限制：

- Runner 自身会先复制到临时目录，避免被安装器替换时失效。
- 同一 appId 发现多个不同安装目录时立即失败；不会迁移、创建第二份、扫描其他目录或根据应用名猜路径。
- 进程先有 30 秒正常退出时间。只有实际 PID 的 exe 路径与注册表 `ExecutablePath` **严格一致**时，Runner 才可终止它；路径不符或无法结束即失败。
- Inno 参数固定为：

```text
/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
/DIR="<InstallLocation>"
/LOG="<本地 Inno 日志>"
```

- 安装成功必须同时满足：退出码为 0、安装日志存在、`InstallLocation` 未变、`ExecutablePath` 未迁移、主 exe 存在、注册表/manifest/主 exe 文件版本均为目标版本。

## 安装、卸载与快捷方式

- 首次安装可选目录；发现相同 `appId` 时只能更新已有 `InstallLocation`，不能在其他目录创建第二份。
- 标准快捷方式目标是 `HonsenUpdateRunner.exe launch`，但图标明确取 `Honsen DrawTranslate.exe`，以保持用户看到的应用图标一致。
- 静默更新后只有 Runner 负责重启；安装器的 `[Run]` 项以 `postinstall` 限制为手动安装场景。
- 卸载只删除该应用的 `{app}` 目录及 `honsen.cad-translator` 专属注册表键；绝不能删除共享的 `Honsen Program` 根目录、其他 Honsen 应用或它们的数据。

## 发布源与镜像现状

当前 Runner 的自动更新源是 `UpdateManifestUrl` 指向的 **GitHub Release**。它只接受公开、稳定、版本更高、资产名匹配且 GitHub API 返回 `sha256:` digest 的 Release。

Gitee 当前用于 Git 仓库、标签和 Release 镜像同步；**当前 Runner 不从 Gitee 检查或下载更新**。如未来加入 Gitee 故障切换，应仍保持同一 Runner、同一 SHA-256 校验和同一安全验证流程，不能让主程序或工具箱直接覆盖文件。

## 当前迁移状态

- Runner 已承担快捷方式启动、自行检查更新和工具箱 `apply` 更新。
- 主程序遗留的更新检查/下载 UI 仍存在，最终替换动作已交给 Runner；在正式清除遗留逻辑前，应继续完成独立真实安装环境中的 `launch`、工具箱 `apply`、失败结果提示与 Runner 缺失提示 E2E 验证。
