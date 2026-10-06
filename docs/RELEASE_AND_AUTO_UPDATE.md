# Windows 发布与自动更新规范

> 本文受 [UPDATE_RELEASE_CONTRACT.md](UPDATE_RELEASE_CONTRACT.md) 约束；该文件是更新与发布方案的最高优先级规范。

本规范是 Windows 版本发布的唯一操作顺序。发布者和后续 agent 必须同时阅读本文件、[PRD_v1.10.1.md](PRD_v1.10.1.md)、[HONSEN_UPDATE_RUNNER.md](HONSEN_UPDATE_RUNNER.md)、[TEST_RULES.md](TEST_RULES.md) 与 `installer/` 下的两个脚本。

## 自动更新链路

```text
快捷方式/工具箱 → HonsenUpdateRunner.exe → GitHub releases/latest → 下载并校验
→ 等待目标进程退出 → /DIR 覆盖原安装目录 → 验证 → 按请求启动主程序
```

客户端只接受比内置版本号更高的**公开稳定版** GitHub Release，并且该 Release 必须带有与版本号完全一致的 Windows 资产：

- `Honsen_DrawTranslate_vX.Y.Z_Setup.exe`（当前格式）；或
- `HonsenCAD.vX.Y.Z.exe`（兼容旧格式）。

GitHub API 必须为该资产返回 `sha256:` digest。缺少 digest、资产名不匹配、版本不高于客户端、预发布版本或校验失败时，客户端必须拒绝自动安装。

## 发布新版本

发布远端固定为 GitHub `origin`（`https://github.com/etianwang/CAD_translator.git`）和 Gitee `gitee`（`https://gitee.com/etianwang/CAD-translator.git`）。每次 `main` 或发布标签推送必须同步发送到两者；任一失败即阻断发布完成。GitHub Release 仍是唯一自动更新源。

1. 选择严格递增的 `X.Y.Z` 版本号。至少同步更新：
   - `backend/updater.py` 的 `CURRENT_VERSION`；
   - `backend/translator.py`、`desktop/launcher.py`、`frontend/package*.json`、`frontend/src/App.jsx`；
   - `changelog.json`；
   - `installer/Honsen_DrawTranslate_Setup.iss` 的 `MyAppVersion`（`MyAppExeName` 必须固定为 `Honsen DrawTranslate.exe`）；
   - `honsen.app.json` 的 `version` 和 `Honsen_DrawTranslate_version_info.txt` 的文件/产品版本；
   - `installer/build_installer.ps1` 的 spec 和安装包文件名；
   - 新建对应的 `Honsen_CAD_Translator_vX.Y.Z.spec`，并更新 README 的 Windows 构建命令。
2. 运行最低检查：

   ```powershell
   python -m unittest tests.test_updater
   python -m compileall -q backend desktop run.py
   Push-Location frontend; npm run build; Pop-Location
   .\installer\build_installer.ps1
   git diff --check
   ```

   `build_installer.ps1` 会重新构建前端、EXE 和 Inno 安装包；它必须发现 `dist\ODAFileConverter\ODAFileConverter.exe`，否则不得作为完整 DWG 发行包发布。
3. 确认 `dist\Honsen DrawTranslate.exe` 与 `installer\Output\Honsen_DrawTranslate_vX.Y.Z_Setup.exe` 存在，计算安装包本地 SHA-256。安装包只作为 Release 资产，`installer/Output/` 必须保持 Git 忽略，绝不能提交二进制文件。
4. 提交源代码，创建带注释的 `vX.Y.Z` 标签，并依次执行；四次均成功才能继续：

   ```powershell
   git push origin main
   git push gitee main
   git push origin vX.Y.Z
   git push gitee vX.Y.Z
   ```
5. 在 GitHub 创建**非 draft、非 prerelease**的 Release，上传上一步的安装包；随后调用 GitHub API/CLI 检查资产 `digest`，它必须等于本地 SHA-256。例如：

   ```powershell
   gh release create vX.Y.Z "installer\Output\Honsen_DrawTranslate_vX.Y.Z_Setup.exe#Honsen_DrawTranslate_vX.Y.Z_Setup.exe" --repo etianwang/CAD_translator --title vX.Y.Z --notes "发布说明"
   gh release view vX.Y.Z --repo etianwang/CAD_translator --json url,isDraft,isPrerelease,assets
   ```

   只有 GitHub Release 是自动更新源；Gitee 用于仓库和标签同步，不替代 GitHub Release。
6. 在 `docs/MEMORY.md` 记录版本、提交、标签、Release URL、安装包大小、SHA-256、通过的检查和未执行的 E2E 项；如该记录在 Release 后新增，再将它作为独立文档提交推送。

## 共享更新助手不可破坏的约束

完整协议见 [HONSEN_UPDATE_RUNNER.md](HONSEN_UPDATE_RUNNER.md)。主程序不得直接启动 Inno：它只启动同目录、由 `honsen.app.json` 声明的 `HonsenUpdateRunner.exe`，传入当前 PID、下载器返回的 SHA-256、目标版本和自身真实运行目录。工具箱必须从固定 appId 注册表键读取 `UpdateRunnerPath` 与 `InstallLocation` 后调用同一文件。

安装器必须安装 `HonsenUpdateRunner.exe` 和 `honsen.app.json`，并在 `HKLM\Software\Honsen Program\Apps\honsen.cad-translator` 写入 `UpdateRunnerPath`。Runner 是唯一有权启动 Inno 的组件，且固定传入：

```text
/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="<target-dir>" /LOG="<result-log>"
```

静默更新的重启由 Runner 在全部验证成功后完成。因此 `installer/Honsen_DrawTranslate_Setup.iss` 的主程序 `[Run]` 项只能供手动安装使用：

```iss
Filename: "{app}\{#MyAppExeName}"; Flags: nowait runasoriginaluser postinstall
```

`postinstall` 确保 `/VERYSILENT` 不会越过 Runner 自行启动程序；`runasoriginaluser` 保证手动安装的启动使用原登录用户。`tests.test_updater` 中的静态回归检查必须保留。

主 EXE 的安装名永久固定为 `Honsen DrawTranslate.exe`，不能再附带版本号。`[InstallDelete]` 只能匹配本产品的 `Honsen DrawTranslate v*.exe` 与 `Honsen_CAD_Translator_v*.exe` 历史文件；禁止使用 `{app}\*.exe`。安装器自身创建的标准桌面和开始菜单快捷方式固定命名为 `Honsen CAD 翻译器`，由 `[Icons]` 在该已知路径替换。桌面、开始菜单和任务栏固定项其余部分属于用户数据：安装器绝不能扫描、重定向或批量改写用户的 `.lnk` 文件。用户固定 `Honsen CAD 翻译器` 后，因 EXE 路径稳定，后续升级无需更改任务栏链接。

真实覆盖式静默安装会改动本机已安装的软件；优先在隔离测试环境执行。没有该环境时，至少完成 updater 单测、Inno 编译和 Release digest 核验，并在 Memory 中明确真实安装 E2E 未执行。
