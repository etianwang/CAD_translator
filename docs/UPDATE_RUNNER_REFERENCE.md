# Windows 独立更新执行器：实施参考与踩坑清单

适用于多个 Windows 桌面应用共用“独立更新助手 + 主程序轻量展示”的架构。

## 推荐职责划分

只有 `ProductUpdateRunner.exe` 可以等待/结束旧进程、运行安装器、覆盖、验证、重启和写结果文件。Runner 可以自行检查、下载和校验 SHA-256；主程序与工具箱也可下载，但必须先校验 SHA-256，且不得直接覆盖、移动、删除或安装应用文件。

主程序可调用 Runner 的 `check` 并读取其结果文件来展示更新内容；用户确认更新后，主程序调用 `launch`/`apply --wait-pid <pid>` 并正常退出。Runner 等待 PID 后执行更新。主程序若提前退出失败，Runner 可在有限条件下强制退出，见下文。

建议命令：

```text
ProductUpdateRunner.exe check  --app-id <appId>
ProductUpdateRunner.exe launch --app-id <appId> --wait-pid <pid>
ProductUpdateRunner.exe apply  --source app|toolbox --app-id <appId> --wait-pid <pid> --installer <absolute-path> --sha256 <hex> --target-dir <install-dir> --expected-version <version> --restart true|false --operation-id <GUID> --result-path <absolute-result-path>
ProductUpdateRunner.exe repair --app-id <appId>
```

## 身份、路径与注册表

每个应用使用永久 appId。安装器在 HKLM（全电脑安装）或 HKCU（当前用户安装）写入唯一应用键，并至少包含：

```text
AppId
Version
InstallLocation
ExecutablePath
LauncherPath
UpdateRunnerPath
UpdateManifestUrl
```

`LauncherPath` 和 `UpdateRunnerPath` 都指向 Runner 的绝对路径。Runner 在任何写入前必须验证：appId、注册表、`InstallLocation`、`ExecutablePath`、Runner 路径和 `<InstallLocation>\product.app.json` 一致。若相同 appId 出现不同安装目录，立即失败；不得猜测路径、扫描磁盘、迁移目录或创建第二份安装。

标准桌面与开始菜单快捷方式应指向 `ProductUpdateRunner.exe launch`，因此 Runner 必须使用与主 EXE 相同图标。

## Runner 更新过程

1. 从安装目录复制 Runner 到 `%TEMP%\Vendor\UpdateRunner\<GUID>\`，由临时副本继续工作，避免覆盖自身时被锁定。
2. 使用以 appId 命名的 Windows mutex，串行化所有入口。
3. Runner 从 `UpdateManifestUrl` 读取稳定版本、安装包 URL、发布说明与 SHA-256；不要让主程序另行下载。
4. 下载完成后再次计算 SHA-256；不匹配立即删除临时文件并失败。
5. 等待主程序 PID 正常退出 30 秒。仍未退出时，使用 `QueryFullProcessImageNameW` 验证 PID 的实际 EXE 路径严格等于注册表 `ExecutablePath`；仅此时可 `TerminateProcess`，再确认退出。绝不按进程名结束进程。
6. 以 UAC `runas` 启动 Inno，并等待退出：

```text
/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="<InstallLocation>" /LOG="<absolute-log-path>"
```

7. 成功要求：退出码 0、日志存在、InstallLocation 未改变、ExecutablePath 未离开原目录、主 EXE 存在、注册表/manifest/EXE 文件版本均等于目标版本。
8. 仅 `--restart true` 时，通过验证后的注册表 `ExecutablePath` 启动应用。

## 用户体验

Runner 应为 `console=False`，避免闪黑框。使用自身原生进度窗口，而不是 Inno 向导：展示检查、发布说明、下载百分比、等待退出、安装、验证和启动。

更新提示提供三个选择：

- 立即更新；
- 稍后提醒：直接启动当前程序，下次再检查；
- 跳过此版本：只保存当前目标版本；出现更高版本时必须再次提示。

将跳过偏好保存到用户目录；不要永久关闭更新提醒。

## 结果、失败与主程序兜底

结果必须原子写入：

```text
%LOCALAPPDATA%\Vendor\UpdateResults\<appId>\<operationId>.json
```

每个发起方生成 GUID，并只读取自己传入的结果路径，不能读取共享“最新结果”。结果固定包含 `appId`、`status`、`source`、`fromVersion`、`toVersion`、`step`、`installerExitCode`、`installerLogPath`、`message`、`completedAtUtc`（以及 `operationId`）。捕获所有异常；不要让未处理异常只表现为“黑框闪退”。

主程序只检查 Runner/manifest/注册表一致性，读取结果展示状态，并提供“重新启动更新服务”入口。Runner 缺失、损坏或上次失败时提示用户通过工具箱修复；主程序自身不得退化为直接安装器。

## 安装与卸载

首次安装允许选目录；已有同 appId 时必须锁定为已有 `InstallLocation`。更新永远传入该目录的 `/DIR`。

卸载只能删除 `{app}` 和当前 appId 的注册表键，绝不可删除共享父目录（例如 `C:\Program Files\Vendor`）或其他应用注册表键。

## 已遇到的真实问题

1. Runner 注册表读取漏掉 `UpdateManifestUrl`，后续访问字段触发未处理 `KeyError`，导致黑框闪退、未更新、结果文件无错误信息。所有必需字段必须在读取时验证，并有异常总捕获。
2. Runner 默认控制台子系统会让快捷方式启动时闪黑框；构建时必须 `console=False`。
3. 快捷方式改指向 Runner 后会显示 Runner 默认图标；Runner 必须嵌入主应用图标。
4. UI 底部版本号可能有独立硬编码，即使 EXE、manifest 和注册表版本更新也会显示旧号。使用唯一版本常量或构建注入，不要散落硬编码。
5. 首个引入 Runner 的版本无法由更旧版本自动获得 Runner，必须手动安装一次。用后续小版本进行真实更新验收。
6. 发布不良 Release 后应删除 Release 与资产，保留 Git 标签/提交便于追溯；不要让 `releases/latest` 继续命中不良包。

## 发布与验收顺序

1. 发布手动迁移基线版本，例如 `X.Y.0`。
2. 在 Windows Sandbox/独立测试机手动安装该版本。
3. 发布 `X.Y.1`，由已安装基线通过快捷方式/工具箱升级。
4. 验证成功更新、工具箱 `apply --restart false`、错误 hash、安装器失败、Runner 缺失、跳过/稍后、主程序无法正常退出、共享父目录卸载安全。
5. 真实 E2E 全部通过后，才删除历史主程序下载/安装代码。
