# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules
spec_dir = os.path.dirname(os.path.abspath(SPEC))
data_files = ["changelog.json", "license_public_key.txt", "honsen.app.json"]
glossary_files = ["translation_abbreviations.yaml", "translation_context_zh_to_fr.yaml", "translation_context_fr_to_zh.yaml", "translation_context_zh_to_en.yaml", "translation_context_en_to_zh.yaml", "translation_corrections.yaml"]
datas = [(os.path.join(spec_dir, name), ".") for name in data_files]
datas += [(os.path.join(spec_dir, "images", "support", name), os.path.join("images", "support")) for name in ("qr_wx.jpg", "qr_ali.jpg")]
datas += [(os.path.join(spec_dir, "glossaries", name), "glossaries") for name in glossary_files]
for folder, _, names in os.walk(os.path.join(spec_dir, "frontend", "dist")):
    for name in names: datas.append((os.path.join(folder, name), os.path.join("frontend", "dist", os.path.relpath(folder, os.path.join(spec_dir, "frontend", "dist")))))
hiddenimports = ["backend.api", "backend.cad", "backend.language_assets", "backend.licensing", "backend.providers.azure", "backend.queue", "backend.storage", "backend.text_cleaning", "backend.translator", "backend.updater", "desktop.launcher", "desktop.native_bridge", "python_multipart", "ezdxf.addons.odafc", "pythonnet", "clr_loader"] + collect_submodules("uvicorn") + collect_submodules("starlette")
a = Analysis(["run.py"], pathex=[spec_dir], binaries=[], datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Honsen DrawTranslate", console=False, icon=[os.path.join(spec_dir, "ico.ico")], version=os.path.join(spec_dir, "Honsen_DrawTranslate_version_info.txt"))
