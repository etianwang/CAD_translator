# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('text_cleaning_utils.py', '.'), ('gui.py', '.'), ('translator.py', '.'), ('config_manager.py', '.'), ('logger.py', '.'), ('cad_file_manager.py', '.'), ('text_cleaner.py', '.'), ('translation_abbreviations.yaml', '.'), ('translation_context_fr_to_zh.yaml', '.'), ('translation_context.yaml', '.'), ('translation_corrections.yaml', '.'), ('changelog.json', '.'), ('background.png', '.'), ('icon.ico', '.')],
    hiddenimports=['googletrans', 'deepl', 'ezdxf', 'openai', 'httpx', 'yaml'],
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
    name='Honsen_CAD_Translator',
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
    icon=['ico.ico'],
)
