# HonsenUpdateRunner 更新协议

`HonsenUpdateRunner.exe` 是 Windows 应用更新的唯一安装、替换、验证和重启执行者。Runner 的 `launch` 可以自行检查、下载并校验更新；主程序和 Honsen 工具箱也可以下载，但必须先校验 SHA-256，随后只调用同一个 Runner。`--source` 只记录发起方，不改变任何安全校验或替换逻辑。

Runner 使用 Windows 无控制台子系统：从快捷方式启动或自动更新时不得显示命令提示符窗口；诊断信息写入结果 JSON 和 Inno 日志，而非标准输出。
Runner 必须使用与 `Honsen DrawTranslate.exe` 相同的应用图标，因为标准桌面和开始菜单快捷方式指向 Runner。
Runner 必须显示原生更新进度窗口，至少覆盖检查、下载（有 Content-Length 时显示百分比）、等待退出、安装、验证和启动阶段。Inno 仍以 `/VERYSILENT` 后台执行；这里的“非静默”指用户可见 Runner 状态，而非显示 Inno 向导。
发现新版时，窗口必须展示 GitHub Release 的版本号和发布说明，再继续下载。
同一个 Runner 进度窗口内提供“立即更新”“稍后提醒”“跳过此版本”三个按钮，不得另开系统确认对话框：稍后仅启动当前程序；跳过版本保存在 `%LOCALAPPDATA%\Honsen Program\UpdatePreferences\<appId>.json`，仅抑制同一目标版本，发现更高版本时必须重新提示。

## 命令

```text
HonsenUpdateRunner.exe apply --source app|toolbox --app-id <appId> --wait-pid <pid> --installer <verified-installer> --sha256 <sha256> --target-dir <install-dir> --expected-version <version> --restart true|false --operation-id <GUID> --result-path <absolute-result-path>
```

工具箱调用示例（下载和 SHA-256 验证完成后）：

```powershell
$appId = 'honsen.cad-translator'
$key = "HKLM:\Software\Honsen Program\Apps\$appId"
$app = Get-ItemProperty $key
$operationId = [guid]::NewGuid().ToString()
$resultPath = Join-Path $env:LOCALAPPDATA "Honsen Program\UpdateResults\$appId\$operationId.json"
& $app.UpdateRunnerPath apply --source toolbox --app-id $appId --wait-pid 0 `
  --installer 'C:\Temp\Honsen_DrawTranslate_v1.10.1_Setup.exe' `
  --sha256 '<verified-sha256>' --target-dir $app.InstallLocation `
  --expected-version '1.10.1' --restart false `
  --operation-id $operationId --result-path $resultPath
# Read only $resultPath after the runner exits.
```

应用自身必须从其运行目录的 `honsen.app.json` 读取 `appId`、`executable` 与 `updateRunner`，并将该运行目录作为 `--target-dir`。当前 CAD 同时保留旧的 `executableName`、`updateRunnerName` 以兼容已安装版本。工具箱必须从 `HKLM\Software\Honsen Program\Apps\<appId>` 读取 `UpdateRunnerPath` 和 `InstallLocation`；不得按显示名称猜测路径或扫描磁盘。

## Runner 的固定规则

1. 验证安装包 SHA-256，并验证 appId、目标目录、`honsen.app.json`、注册表 `InstallLocation`、`ExecutablePath`、`UpdateRunnerPath` 一致。
2. 使用 appId 命名的全局 Windows mutex 排他执行；只等待指定 PID 自行退出，从不以固定延时或强杀替代等待。
3. 仅以 `/DIR="<target-dir>"` 静默执行 Inno，参数固定为 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-`，并为本次 operation 写入同目录的 `.inno.log`。
   Runner 先等待主程序 30 秒正常退出；仅当该 PID 的实际 EXE 路径严格等于注册表 `ExecutablePath` 时，才可终止该 PID 并再次等待退出。路径不符或终止失败必须停止更新。
4. 等待安装器退出，要求退出码为零、日志存在、注册表和 manifest 都等于预期版本，且新主 EXE 的 Windows 文件版本匹配预期版本。
5. 将成功或失败的最终 JSON 原子写入 `%LOCALAPPDATA%\Honsen Program\UpdateResults\<appId>\<operationId>.json`。结果字段固定为 `appId`、`status`、`source`、`fromVersion`、`toVersion`、`step`、`installerExitCode`、`installerLogPath`、`message`、`completedAtUtc`（并包含 `operationId`）；只有 `--restart true` 的成功任务启动注册表中的 `ExecutablePath`。

安装器在静默模式下不自行重启应用；手动安装仍可显示启动复选项。首个采用本协议的版本必须手动安装一次，因为更早的安装目录不包含 Runner、manifest 或 `UpdateRunnerPath`。
