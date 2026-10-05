"""Native file dialogs exposed to the React UI via pywebview."""

import os
import json
import subprocess
import sys
import threading
from pathlib import Path
from datetime import datetime

import webview


class NativeBridge:
    @staticmethod
    def _window():
        if not webview.windows:
            raise RuntimeError("桌面窗口尚未就绪")
        return webview.windows[0]

    def _open_dialog(self, *, multiple: bool = False, file_types=()) -> list[str]:
        paths = self._window().create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=multiple,
            file_types=file_types,
        )
        return list(paths or ())

    def _save_dialog(self, filename: str, file_types=()) -> str:
        paths = self._window().create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=filename,
            file_types=file_types,
        )
        return str(paths[0]) if paths else ""

    def pick_dxf_file(self) -> dict:
        return self.pick_cad_file()

    def pick_cad_file(self) -> dict:
        paths = self._open_dialog(file_types=("CAD files (*.dxf;*.dwg)", "All files (*.*)"))
        path = paths[0] if paths else ""
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
        return {"paths": self._open_dialog(multiple=True, file_types=("CAD files (*.dxf;*.dwg)",))}

    def pick_output_dir(self) -> dict:
        paths = self._window().create_file_dialog(webview.FOLDER_DIALOG)
        path = str(paths[0]) if paths else ""
        return {"path": path or ""}

    def pick_term_package(self) -> dict:
        paths = self._open_dialog(file_types=("Honsen term package (*.hcterms.json)", "JSON files (*.json)"))
        path = paths[0] if paths else ""
        return {"path": path or ""}

    def save_term_package(self) -> dict:
        path = self._save_dialog("项目术语.hcterms.json", ("Honsen term package (*.hcterms.json)",))
        return {"path": path or ""}

    def export_logs(self) -> dict:
        path = self._save_dialog(
            f"Honsen_CAD_Translator_log_{datetime.now():%Y%m%d_%H%M%S}.txt",
            ("Text files (*.txt)",),
        )
        if not path:
            return {"path": ""}
        from backend.api import service
        service.export_logs(path)
        return {"path": path}

    def reveal_file(self, path: str) -> dict:
        if not path or not os.path.isfile(path):
            return {"error": "输出文件不存在，可能已被移动或删除"}
        normalized = os.path.normpath(path)
        if sys.platform == "win32":
            command = ["explorer.exe", "/select,", normalized]
        elif sys.platform == "darwin":
            command = ["open", "-R", normalized]
        else:
            command = ["xdg-open", os.path.dirname(normalized)]
        try:
            subprocess.Popen(command)
        except OSError as exc:
            return {"error": f"无法在文件管理器中定位输出文件: {exc}"}
        return {"ok": True}

    def minimize_window(self) -> None:
        if webview.windows:
            webview.windows[0].minimize()

    def close_window(self) -> None:
        from backend.api import service
        from backend.cad import unmount_embedded_odafc
        service.shutdown()
        unmount_embedded_odafc()
        if webview.windows:
            webview.windows[0].destroy()
        os._exit(0)

    def install_update(self, installer_path: str, sha256: str, expected_version: str) -> dict:
        """Hand the verified package to the installed shared update runner."""
        path = os.path.abspath(installer_path)
        app_dir = Path(sys.executable).resolve().parent
        try:
            metadata = json.loads((app_dir / "honsen.app.json").read_text(encoding="utf-8"))
            app_id = metadata["appId"]
            runner = app_dir / metadata["updateRunnerName"]
        except (OSError, ValueError, KeyError, TypeError):
            return {"error": "当前安装缺少 HonsenUpdateRunner，请手动安装包含更新助手的新版本一次"}
        if sys.platform != "win32" or not os.path.isfile(path) or not runner.is_file() or not sha256 or not expected_version:
            return {"error": "自动更新仅支持经过校验的 Windows 安装包"}
        try:
            subprocess.Popen([
                str(runner), "apply", "--source", "app", "--app-id", str(app_id),
                "--wait-pid", str(os.getpid()), "--installer", path, "--sha256", sha256,
                "--target-dir", str(app_dir), "--expected-version", expected_version, "--restart", "true",
            ], cwd=str(app_dir))
            threading.Thread(target=self.close_window, daemon=True).start()
            return {"ok": True}
        except OSError as exc:
            return {"error": f"无法启动更新安装包: {exc}"}

    def update_service_status(self) -> dict:
        app_dir = Path(sys.executable).resolve().parent
        try:
            meta = json.loads((app_dir / "honsen.app.json").read_text(encoding="utf-8"))
            runner = app_dir / meta["updateRunnerName"]
            if not runner.is_file(): raise OSError()
            return {"ok": True, "message": "更新服务正常"}
        except (OSError, ValueError, KeyError):
            return {"ok": False, "message": "更新服务异常，请通过 Honsen工具箱修复"}

    def restart_update_service(self) -> dict:
        status = self.update_service_status()
        if not status["ok"]: return {"error": status["message"]}
        runner = Path(sys.executable).resolve().parent / "HonsenUpdateRunner.exe"
        subprocess.Popen([str(runner), "launch", "--wait-pid", str(os.getpid())])
        threading.Thread(target=self.close_window, daemon=True).start()
        return {"ok": True}
