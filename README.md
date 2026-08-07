# Honsen CAD 中法英互译工具 v1.7.0

面向机电与建筑图纸的桌面翻译工具：读取 CAD 图纸中的文字，调用 DeepL 完成**中文、法语、英语**之间的双向翻译后写回新文件。默认提供 React 桌面界面，也保留 Tkinter 旧版界面。

![界面预览](images/demo.png)

## 功能

- 支持 `.dxf` 直接翻译；安装 ODA File Converter 后支持 `.dwg`。
- 支持中文→法语、法语→中文、中文→英语和英语→中文四种方向。
- 内置中法、法中、中英和英中的 CAD 术语表；完整匹配的图纸标签会直接采用术语表译文，其他文本交由 DeepL 翻译。
- 翻译模型空间、布局中的 `TEXT`、`MTEXT`、`ATTDEF`、`ATTRIB` 和 `MULTILEADER` 文字；可选择继续扫描块定义中的文字。
- 针对 CAD/MTEXT 格式控制符、乱码字符、尺寸和缩写进行清洗，内置机电常用术语、法语缩写和译文修正规则。
- DWG 会自动执行“DWG → DXF → 翻译 → DWG”，并尽量按原始 DWG 版本输出。
- 界面显示翻译日志和进度，DeepL Key 保存到用户目录的 `~/.cad_translator_config.json`；也可通过环境变量 `DEEPL_API_KEY` 提供。

## 环境要求

- Windows 10/11（桌面界面使用 WebView2；Windows 11 通常已内置）。
- Python 3 和 Node.js（从源码运行或构建时需要）。
- 有效的 [DeepL API Key](https://www.deepl.com/pro-api)。
- 仅翻译 DXF 时不需要其他组件；翻译 DWG 还需 [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)。

## 从源码运行

```powershell
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python main.py
```

打开程序后，选择输入图纸和输出目录，填写 DeepL API Key，选择翻译方向，然后开始翻译。输出文件会保留源文件扩展名，默认以 `fr_` 或 `zh_` 加时间戳命名。

若透明窗口在设备上显示异常，可改用不透明窗口：

```powershell
$env:CAD_UI_OPAQUE = '1'
python main.py
```

开发前端界面时，可分别启动 API 和 Vite：

```powershell
# 终端 1
python -c "import uvicorn; from web_api import app; uvicorn.run(app, host='127.0.0.1', port=8765)"

# 终端 2
cd frontend
npm run dev
```

然后访问 `http://localhost:5173`。如需旧版 Tkinter 界面，运行：

```powershell
python main.py --legacy
```

## DWG 支持

程序按以下顺序寻找 `ODAFileConverter.exe`：

1. 环境变量 `CAD_ODA_EXEC` 指定的完整路径；
2. 主程序同级的 `ODAFileConverter/ODAFileConverter.exe`；
3. 主程序同级的 `ODAFileConverter.exe`；
4. `C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe`。

未找到 ODA 时，仍可翻译 DXF；DWG 需要先安装 ODA，或自行在 CAD 软件中另存为 DXF。分发 ODA 时请遵守其许可条款。

## 打包 Windows 程序

先构建前端并安装 PyInstaller：

```powershell
pip install pyinstaller
cd frontend
npm install
npm run build
cd ..
pyinstaller Honsen_CAD_Translator_v1.7.0.spec
```

生成的程序位于 `dist/Honsen_CAD_Translator_v1.7.0.exe`。若希望安装包开箱支持 DWG，请将 ODA File Converter 的完整目录放到 `dist/ODAFileConverter/`。

安装 Inno Setup 6 后，可一键生成安装包：

```powershell
.\installer\build_installer.ps1
```

输出为 `installer_output/Honsen_CAD_Translator_v1.7.0_Setup.exe`。

## 项目结构

```text
main.py                 翻译核心与 Tkinter 旧版界面入口
web_launcher.py         FastAPI 与 pywebview 桌面窗口启动器
web_api.py              React 界面使用的本地 API 与任务服务
cad_convert.py          DXF/DWG 与 ODA File Converter 的转换流程
text_cleaning_utils.py  CAD 文本清洗和 MTEXT 写回处理
frontend/               React + Vite 界面
installer/              Inno Setup 安装包脚本
```

## 注意事项

- 翻译依赖网络和 DeepL API；API 配额、费用和支持的语言以 DeepL 的规则为准。
- 术语表适合标准化图纸标签（如“天花图”“桥架”“剪力墙”）；包含多个语义的长句仍应在输出图纸中复核。
- 图纸格式复杂、含自定义实体或由特定 CAD 软件导出时，建议先备份原图并检查输出结果。
- 本工具只写入输出文件，不会直接覆盖所选的源图纸。
