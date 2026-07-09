# CAD_translator

### 项目简介
这是一个基于 `ezdxf` 的 CAD 翻译小工具，专为机电专业设计。  
能帮你快速搞定图纸里的外文翻译，省去手动查词、手动修改的麻烦。

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

### 注意事项 (必读)

1. **支持 DXF / DWG：** 可直接选择 `.dxf` 或 `.dwg`。DWG 会通过本机 **ODA File Converter**（ezdxf odafc 插件）自动转为 DXF R2010 翻译，完成后按原 DWG 版本写回。
2. **ODA 安装：** 安装包会将 ODA 与主程序放在**同一目录**。推荐结构：

   ```
   安装目录/
     Honsen_CAD_Translator_v2.2.exe
     ODAFileConverter/
       ODAFileConverter.exe
       （ODA 自带 DLL 等文件）
   ```

   程序会**优先**使用同目录下的 ODA，找不到时再尝试系统路径 `C:\Program Files\ODA\...`。  
   也可通过环境变量 `CAD_ODA_EXEC` 指定完整 exe 路径。  
   单独安装：[ODA File Converter 下载](https://www.opendesign.com/guestfiles/oda_file_converter)
3. **天正软件的坑：**  
   天正导出的 DXF 偶尔会有文字乱码问题，这是软件编码差异导致的，请见谅。
4. **DeepL 翻译：**  
   内置了机电行业的常用词汇表，翻译更专业。使用前请配置 DeepL API Key（界面中填写，或设置环境变量 `DEEPL_API_KEY`）。
5. **支持的文字类型：** TEXT、MTEXT、块属性（ATTDEF/ATTRIB，含提示 Prompt）、多重引线（MULTILEADER）。

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
- 旧版界面：`Honsen_CAD_Translator_v2.2.exe --legacy`
