# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\Project\\Py\\CAD_translator\\translation_abbreviations.yaml', '.'), ('E:\\Project\\Py\\CAD_translator\\translation_context.yaml', '.'), ('E:\\Project\\Py\\CAD_translator\\translation_context_fr_to_zh.yaml', '.'), ('E:\\Project\\Py\\CAD_translator\\translation_corrections.yaml', '.'), ('E:\\Project\\Py\\CAD_translator\\changelog.json', '.'), ('E:\\Project\\Py\\CAD_translator\\ico.ico', '.'), ('E:\\Project\\Py\\CAD_translator\\icon.ico', '.'), ('E:\\Project\\Py\\CAD_translator\\README.md', '.')],
    hiddenimports=['ezdxf', 'googletrans', 'deepl', 'openai', 'yaml', 'text_cleaning_utils'],
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
    icon=['E:\\Project\\Py\\CAD_translator\\ico.ico'],
)
