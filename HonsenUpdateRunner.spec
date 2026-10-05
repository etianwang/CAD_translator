# -*- mode: python ; coding: utf-8 -*-
"""Standalone updater. It must remain outside the app process being replaced."""
import os

spec_dir = os.path.dirname(os.path.abspath(SPEC))
a = Analysis(["desktop/update_runner.py"], pathex=[spec_dir], binaries=[], datas=[], hiddenimports=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="HonsenUpdateRunner", console=False, icon=[os.path.join(spec_dir, "ico.ico")])
