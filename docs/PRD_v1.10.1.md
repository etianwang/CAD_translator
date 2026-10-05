# v1.10.1 PRD：统一更新执行器

> 历史 PRD。当前更新、工具箱、安装器、卸载和发布的强制规范以 [UPDATE_RELEASE_CONTRACT.md](UPDATE_RELEASE_CONTRACT.md) 为准；每个新 agent 与新对话必须先阅读该文件。

## 固定应用标识

- appId：`honsen.cad-translator`
- 主程序：`Honsen DrawTranslate.exe`
- 唯一更新/启动执行器：`HonsenUpdateRunner.exe`

## 目标与边界

Runner 是唯一可以提权运行 Inno、覆盖文件、验证版本、重启应用、写更新结果的程序。Runner 的 `launch` 可以检查、下载和校验 SHA-256；主程序和 Honsen 工具箱也可以下载，但必须先校验 SHA-256，且不得移动、删除、覆盖或安装应用文件。

Runner 支持 `launch` 与 `apply`。所有标准桌面/开始菜单快捷方式及工具箱“打开”必须调用 `LauncherPath launch`。`launch` 检查公开稳定 GitHub Release：无更新时启动注册表 `ExecutablePath`；有更新时下载、校验并在原目录静默安装后验证并启动新版。`apply` 供工具箱对已验证安装包发起更新。

## 安全与目录规则

Runner 仅接受 appId `honsen.cad-translator`，并验证 HKLM 或 HKCU 的 Honsen Program 应用记录、`honsen.app.json`、`InstallLocation`、`ExecutablePath`、`UpdateRunnerPath` 一致。出现不同目录的同 appId 记录即失败。Runner 运行时必须复制至 `%TEMP%\Honsen Program\UpdateRunner\<GUID>\`，使用 appId 全局 mutex，并且只以 `/DIR="<InstallLocation>"` 覆盖已注册目录。

Inno 参数固定为 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="<InstallLocation>" /LOG="<log>"`。必须等待指定 PID 实际退出和安装器退出；成功要求退出码 0、日志存在、注册表与 manifest 版本及主 EXE Windows 文件版本均等于目标版本。

## 注册表与结果

`HKLM\Software\Honsen Program\Apps\honsen.cad-translator`（当前全电脑安装）或对应 HKCU 键必须包含 `AppId`、`Version`、`Publisher`、`InstallLocation`、`ExecutablePath`、`LauncherPath`、`UpdateRunnerPath`、`UpdateManifestUrl`。`Publisher` 必须与 manifest 的 `publisher` 一致；`LauncherPath` 与 `UpdateRunnerPath` 均是 Runner 的绝对路径。

每次调用必须携带 `operationId` 和受信任的结果路径；最终结果原子写入 `%LOCALAPPDATA%\Honsen Program\UpdateResults\honsen.cad-translator\<operationId>.json`。结果字段统一为 appId、status、source、fromVersion、toVersion、step、installerExitCode、installerLogPath、message、completedAtUtc（以及 operationId）。

## 主程序兜底与迁移

主程序仅检查 Runner/manifest/注册表一致性、展示结果文件，并提供“重新启动更新服务”（只调用 Runner `launch` 或 `repair`）。Runner 缺失、损坏或上次更新失败时提示“更新服务异常，请通过 Honsen工具箱修复”。

旧主程序更新模块在 Runner 通过隔离环境真实更新、工具箱调用和失败修复 UI 三项验证前保留但不得再由主流程调用；验证后才允许删除。
