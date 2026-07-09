# CAD_translator

### 项目简介
这是一个基于 `ezdxf` 的 CAD 翻译小工具，专为机电专业设计。  
支持 **DXF** 与 **DWG** 图纸翻译，能帮你快速搞定图纸里的外文翻译，省去手动查词、手动修改的麻烦。

> **DWG 说明：** 翻译 `.dwg` 文件需配合 **[ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)** 使用。程序会自动调用 ODA 将 DWG 转为 DXF 进行翻译，完成后写回原格式。若未安装 ODA，仍可直接翻译 **DXF** 文件。

---

### 安装与运行

**新版 React 毛玻璃界面（推荐）：**

```bash
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python main.py
```

整窗透明模式默认开启（WebView2 毛玻璃 + Iridescence 背景）。若透明窗口显示异常，可关闭：

```bash
set CAD_UI_OPAQUE=1
python main.py
```

开发模式（热更新 UI）：

```bash
# 终端 1
python -c "import uvicorn; from web_api import app; uvicorn.run(app, host='127.0.0.1', port=8765)"

# 终端 2
cd frontend && npm run dev
# 浏览器打开 http://localhost:5173
```

**旧版 Tkinter 界面：**

```bash
python main.py --legacy
```

---

### 文件格式与 ODA（必读）

| 格式 | 是否支持 | 说明 |
|------|----------|------|
| **DXF** | ✅ 直接支持 | 选择 `.dxf` 即可翻译，无需额外组件 |
| **DWG** | ✅ 需 ODA | 必须安装 **ODA File Converter**，由程序自动完成 DWG → DXF → 翻译 → DWG |

**DWG 工作流程：**

1. 程序检测到 `.dwg` 文件
2. 调用 ODA File Converter 转为 DXF R2010
3. 在 DXF 上执行翻译并写回文字
4. 再经 ODA 转回与原文件相同版本的 DWG

**ODA 安装方式（任选其一）：**

1. **与主程序同目录（推荐）** — 适合 exe 分发与安装包：

   ```
   安装目录/
     Honsen_CAD_Translator_v5.5.exe
     ODAFileConverter/
       ODAFileConverter.exe
       （ODA 自带全部 DLL 等文件）
   ```

2. **系统安装** — 安装到默认路径后程序会自动识别：  
   `C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe`

3. **环境变量** — 通过 `CAD_ODA_EXEC` 指定 ODA 可执行文件的完整路径

**下载 ODA：** [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)

> 界面中会显示 ODA 是否已就绪。未检测到 ODA 时，**DWG 无法翻译**，请改用 DXF，或在 AutoCAD 中将 DWG「另存为 DXF」后再翻译。

---

### 注意事项

1. **天正软件的坑：**  
   天正导出的 DXF 偶尔会有文字乱码问题，这是软件编码差异导致的，请见谅。
2. **DeepL 翻译：**  
   内置了机电行业的常用词汇表，翻译更专业。使用前请配置 DeepL API Key（界面中填写，或设置环境变量 `DEEPL_API_KEY`）。
3. **支持的文字类型：** TEXT、MTEXT、块属性（ATTDEF/ATTRIB，含提示 Prompt）、多重引线（MULTILEADER）。

### 打包为 exe

**环境要求：** Windows 10/11，目标机器需已安装 [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)（Win11 通常自带）。

**步骤：**

```powershell
# 1. 安装 Python 依赖
pip install -r requirements.txt
pip install pyinstaller

# 2. 构建 React 前端（必须，否则无法打包）
cd frontend
npm install
npm run build
cd ..

# 3. 打包（可选：根目录放 ico.ico 作为程序图标）
pyinstaller Honsen_CAD_Translator_v5.5.spec
```

生成的 exe 位于 `dist/Honsen_CAD_Translator_v5.5.exe`。

**与 ODA 一起分发（安装包）：**

推荐使用 **Inno Setup 6** 生成 Windows 安装程序（`.exe`）：

1. 安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. 将 ODA File Converter **完整文件**放入 `dist/ODAFileConverter/`（与主 exe 同级，可选）
3. 运行一键脚本：

   ```powershell
   .\installer\build_installer.ps1
   ```

   或手动：`pyinstaller Honsen_CAD_Translator_v5.5.spec` 后，用 Inno Setup 编译 `installer/Honsen_CAD_Translator_v5.5.iss`

4. 输出：`installer_output/Honsen_CAD_Translator_v5.5_Setup.exe`

安装后目录结构：

```
C:\Program Files\Honsen CAD Translator\
  Honsen_CAD_Translator_v5.5.exe
  ODAFileConverter\          （若打包时包含）
    ODAFileConverter.exe
    （ODA 自带 DLL 等文件）
```

**注意：**
- **不要将 ODA 打进 PyInstaller 单文件 exe 内**（需独立进程 + 大量 DLL）
- ODA 商业分发需遵守 [ODA 许可](https://www.opendesign.com/faq/question/what-are-oda-viewer-and-oda-file-converter)
- 默认打包的是 **React 新界面**（`python main.py`），不是 Tkinter 旧版
- 首次运行较慢（PyInstaller 解压临时文件）
- 若双击无反应，可临时把 spec 里 `console=False` 改为 `console=True` 查看报错
- 旧版界面：`Honsen_CAD_Translator_v5.5.exe --legacy`
