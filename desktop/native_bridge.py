"""Native file dialogs exposed to the React UI via pywebview."""

import os
import subprocess
import tkinter as tk
from datetime import datetime
from tkinter import filedialog

import webview


class NativeBridge:
    def pick_dxf_file(self) -> dict:
        return self.pick_cad_file()

    def pick_cad_file(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="选择 CAD 文件",
            filetypes=[
                ("CAD files", "*.dxf;*.dwg"),
                ("DXF files", "*.dxf"),
                ("DWG files", "*.dwg"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        if not path:
            return {"path": "", "dir": "", "base": "", "ext": ""}
        base, ext = os.path.splitext(os.path.basename(path))
        return {
            "path": path,
            "dir": os.path.dirname(path),
            "base": base,
            "ext": ext.lower(),
        }

    def pick_cad_files(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        paths = filedialog.askopenfilenames(title="选择 CAD 文件", filetypes=[("CAD files", "*.dxf;*.dwg")])
        root.destroy()
        return {"paths": list(paths)}

    def pick_output_dir(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择输出目录")
        root.destroy()
        return {"path": path or ""}

    def pick_term_package(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(title="选择项目术语包", filetypes=[("Honsen term package", "*.hcterms.json"), ("JSON files", "*.json")])
        root.destroy()
        return {"path": path or ""}

    def save_term_package(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.asksaveasfilename(title="新建项目术语包", defaultextension=".hcterms.json", initialfile="项目术语.hcterms.json", filetypes=[("Honsen term package", "*.hcterms.json")])
        root.destroy()
        return {"path": path or ""}

    def export_logs(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.asksaveasfilename(
            title="导出日志",
            defaultextension=".txt",
            initialfile=f"Honsen_CAD_Translator_log_{datetime.now():%Y%m%d_%H%M%S}.txt",
            filetypes=[("Text files", "*.txt")],
        )
        root.destroy()
        if not path:
            return {"path": ""}
        from backend.api import service
        service.export_logs(path)
        return {"path": path}

    def reveal_file(self, path: str) -> dict:
        if not path or not os.path.isfile(path):
            return {"error": "输出文件不存在，可能已被移动或删除"}
        subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(path)])
        return {"ok": True}

    def minimize_window(self) -> None:
        if webview.windows:
            webview.windows[0].minimize()

    def close_window(self) -> None:
        from backend.api import service
        service.shutdown()
        if webview.windows:
            webview.windows[0].destroy()
        os._exit(0)
