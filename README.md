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

1. **必须转为 DXF：** 软件只认 `.dxf` 文件。  
   如果是 `.dwg` 格式，请先在 AutoCAD 里选“另存为” DXF。
2. **天正软件的坑：**  
   天正导出的 DXF 偶尔会有文字乱码问题，这是软件编码差异导致的，请见谅。
3. **DeepL 翻译：**  
   内置了机电行业的常用词汇表，翻译更专业。使用前请配置 DeepL API Key（界面中填写，或设置环境变量 `DEEPL_API_KEY`）。
4. **支持的文字类型：** TEXT、MTEXT、块属性（ATTDEF/ATTRIB，含提示 Prompt）、多重引线（MULTILEADER）。

### 打包为 exe（可选）

```bash
pyinstaller Honsen_CAD_Translator_v2.2.spec
```

打包前请将 `ico.ico` 放在项目根目录（可选，用于程序图标）。
