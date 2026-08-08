# -*- mode: python ; coding: utf-8 -*-
"""One-file desktop build. Keep ODAFileConverter beside the final EXE."""
import os

from PyInstaller.utils.hooks import collect_submodules

spec_dir = os.path.dirname(os.path.abspath(SPEC))
data_files = [
    "translation_abbreviations.yaml", "translation_context.yaml",
    "translation_context_fr_to_zh.yaml", "translation_context_zh_to_en.yaml",
    "translation_context_en_to_zh.yaml", "translation_corrections.yaml", "changelog.json",
]
datas = [(os.path.join(spec_dir, name), ".") for name in data_files]
for folder, _, names in os.walk(os.path.join(spec_dir, "frontend", "dist")):
    for name in names:
        source = os.path.join(folder, name)
        datas.append((source, os.path.join("frontend", "dist", os.path.relpath(folder, os.path.join(spec_dir, "frontend", "dist")))))

hiddenimports = [
    "azure_translator", "batch_queue", "cad_convert", "native_bridge", "text_cleaning_utils", "web_api", "web_launcher",
    "ezdxf.addons.odafc", "pythonnet", "clr_loader",
] + collect_submodules("uvicorn") + collect_submodules("starlette")

a = Analysis(["main.py"], pathex=[spec_dir], binaries=[], datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name="Honsen_CAD_Translator_v1.8.2",
    console=False, icon=[os.path.join(spec_dir, "ico.ico")],
)
