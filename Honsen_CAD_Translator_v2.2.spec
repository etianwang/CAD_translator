# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_submodules

spec_dir = os.path.dirname(os.path.abspath(SPEC))

_data_files = [
    'translation_abbreviations.yaml',
    'translation_context.yaml',
    'translation_context_fr_to_zh.yaml',
    'translation_corrections.yaml',
    'changelog.json',
]
datas = [(os.path.join(spec_dir, f), '.') for f in _data_files if os.path.exists(os.path.join(spec_dir, f))]

frontend_dist = os.path.join(spec_dir, 'frontend', 'dist')
if os.path.isdir(frontend_dist):
    for dirpath, _, filenames in os.walk(frontend_dist):
        for name in filenames:
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, frontend_dist)
            dest = os.path.join('frontend', 'dist', os.path.dirname(rel))
            datas.append((src, dest))
else:
    raise SystemExit(
        '未找到 frontend/dist，请先构建前端：\n'
        '  cd frontend && npm install && npm run build'
    )

_icon = os.path.join(spec_dir, 'ico.ico')
_icon_arg = [_icon] if os.path.exists(_icon) else []

hiddenimports = [
    'ezdxf',
    'deepl',
    'yaml',
    'text_cleaning_utils',
    'web_api',
    'web_launcher',
    'native_bridge',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'starlette',
    'starlette.routing',
    'pydantic',
    'webview',
    'pythonnet',
    'clr_loader',
]
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('starlette')

a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Honsen_CAD_Translator_v2.2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_arg,
)
