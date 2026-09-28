# Windows 发布与自动更新规范

本规范是 Windows 版本发布的唯一操作顺序。发布者和后续 agent 必须同时阅读本文件、[PRD_v1.9.3.md](PRD_v1.9.3.md)、[TEST_RULES.md](TEST_RULES.md) 与 `installer/` 下的两个脚本。

## 自动更新链路

```text
已安装客户端 → GitHub releases/latest → 下载 Release 安装包 → SHA-256 校验
→ /VERYSILENT 启动 Inno Setup → 关闭旧进程 → 替换 EXE 与 ODA 目录 → 自动启动新 EXE
```

客户端只接受比内置版本号更高的**公开稳定版** GitHub Release，并且该 Release 必须带有与版本号完全一致的 Windows 资产：

- `Honsen_DrawTranslate_vX.Y.Z_Setup.exe`（当前格式）；或
- `HonsenCAD.vX.Y.Z.exe`（兼容旧格式）。

GitHub API 必须为该资产返回 `sha256:` digest。缺少 digest、资产名不匹配、版本不高于客户端、预发布版本或校验失败时，客户端必须拒绝自动安装。

## 发布新版本

1. 选择严格递增的 `X.Y.Z` 版本号。至少同步更新：
   - `backend/updater.py` 的 `CURRENT_VERSION`；
   - `backend/translator.py`、`desktop/launcher.py`、`frontend/package*.json`、`frontend/src/App.jsx`；
   - `changelog.json`；
   - `installer/Honsen_DrawTranslate_Setup.iss` 的 `MyAppVersion` 与 `MyAppExeName`；
   - `installer/build_installer.ps1` 的 spec、EXE 和安装包文件名；
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
3. 确认 `installer\Output\Honsen_DrawTranslate_vX.Y.Z_Setup.exe` 存在，计算本地 SHA-256。安装包只作为 Release 资产，`installer/Output/` 必须保持 Git 忽略，绝不能提交二进制文件。
4. 提交源代码，创建带注释的 `vX.Y.Z` 标签，并将 `main` 与标签同时推送到 GitHub `origin` 和 Gitee `gitee`。
5. 在 GitHub 创建**非 draft、非 prerelease**的 Release，上传上一步的安装包；随后调用 GitHub API/CLI 检查资产 `digest`，它必须等于本地 SHA-256。例如：

   ```powershell
   gh release create vX.Y.Z "installer\Output\Honsen_DrawTranslate_vX.Y.Z_Setup.exe#Honsen_DrawTranslate_vX.Y.Z_Setup.exe" --repo etianwang/CAD_translator --title vX.Y.Z --notes "发布说明"
   gh release view vX.Y.Z --repo etianwang/CAD_translator --json url,isDraft,isPrerelease,assets
   ```

   只有 GitHub Release 是自动更新源；Gitee 用于仓库和标签同步，不替代 GitHub Release。
6. 在 `docs/MEMORY.md` 记录版本、提交、标签、Release URL、安装包大小、SHA-256、通过的检查和未执行的 E2E 项；如该记录在 Release 后新增，再将它作为独立文档提交推送。

## 静默更新重启不可破坏的约束

`desktop/native_bridge.py` 会以 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS` 启动已校验的安装包，再关闭旧程序。因此 `installer/Honsen_DrawTranslate_Setup.iss` 的主程序 `[Run]` 项必须：

```iss
Filename: "{app}\{#MyAppExeName}"; Flags: nowait runasoriginaluser
```

禁止在该项加入 `postinstall` 或 `skipifsilent`：它们会使 `/VERYSILENT` 更新完成后不启动新版本。`runasoriginaluser` 保证 UAC 安装完成后主程序以原登录用户而非管理员身份运行。`tests.test_updater` 中的静态回归检查必须保留。

真实覆盖式静默安装会改动本机已安装的软件；优先在隔离测试环境执行。没有该环境时，至少完成 updater 单测、Inno 编译和 Release digest 核验，并在 Memory 中明确真实安装 E2E 未执行。
