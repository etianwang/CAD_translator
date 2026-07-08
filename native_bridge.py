"""Native file dialogs exposed to the React UI via pywebview."""

import os
import tkinter as tk
from tkinter import filedialog


class NativeBridge:
    def pick_dxf_file(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="选择 DXF 文件",
            filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")],
        )
        root.destroy()
        if not path:
            return {"path": "", "dir": "", "base": ""}
        return {
            "path": path,
            "dir": os.path.dirname(path),
            "base": os.path.splitext(os.path.basename(path))[0],
        }

    def pick_output_dir(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择输出目录")
        root.destroy()
        return {"path": path or ""}
