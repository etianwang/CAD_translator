# -*- mode: python ; coding: utf-8 -*-
import os

spec_dir = os.path.dirname(os.path.abspath(SPEC))

_data_files = [
    'translation_abbreviations.yaml',
    'translation_context.yaml',
    'translation_context_fr_to_zh.yaml',
    'translation_corrections.yaml',
    'changelog.json',
]
datas = [(os.path.join(spec_dir, f), '.') for f in _data_files if os.path.exists(os.path.join(spec_dir, f))]

_icon = os.path.join(spec_dir, 'ico.ico')
_icon_arg = [_icon] if os.path.exists(_icon) else []

a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=datas,
    hiddenimports=['ezdxf', 'deepl', 'yaml', 'text_cleaning_utils'],
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
    icon=_icon_arg,
)
