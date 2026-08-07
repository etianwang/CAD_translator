"""Native file dialogs exposed to the React UI via pywebview."""

import os
import tkinter as tk
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

    def minimize_window(self) -> None:
        if webview.windows:
            webview.windows[0].minimize()

    def close_window(self) -> None:
        from web_api import service
        service.shutdown()
        if webview.windows:
            webview.windows[0].destroy()
        os._exit(0)
