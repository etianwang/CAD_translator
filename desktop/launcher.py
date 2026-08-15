"""Launch FastAPI + pywebview desktop shell for the React UI."""

import os
import sys
import threading
import time
from pathlib import Path

import uvicorn

from desktop.native_bridge import NativeBridge
from backend.api import API_PORT, FRONTEND_DIST, app, service
from backend.cad import unmount_embedded_odafc

TITLE = "Honsen CAD 中法英互译工具 v1.8.8"
_INSTANCE_MUTEX = None


def _webview_gui() -> str | None:
    """Use WebView2 on Windows and the native platform default elsewhere."""
    return "edgechromium" if sys.platform == "win32" else None


def _acquire_single_instance() -> bool:
    """Keep a second desktop window from attaching to an older local API."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        global _INSTANCE_MUTEX
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _INSTANCE_MUTEX = kernel32.CreateMutexW(None, False, "Local\\HonsenCADTranslator")
        return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def _wait_server(url: str, timeout: float = 15.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.15)
    return False


def _enable_windows_acrylic():
    """Windows 10/11 整窗亚克力/透明效果（WebView2）"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, TITLE)
        if not hwnd:
            return
        # DWM 窗口圆角 + 暗色边框
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        pref = wintypes.INT(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(pref),
            ctypes.sizeof(pref),
        )
    except Exception:
        pass


def run_web_app():
    if not _acquire_single_instance():
        print("Honsen CAD Translator is already running.")
        return
    if not FRONTEND_DIST.exists():
        print("未找到 frontend/dist，请先构建 React 界面：")
        print("  cd frontend")
        print("  npm install")
        print("  npm run build")
        sys.exit(1)

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=API_PORT, log_level="warning"))

    api_thread = threading.Thread(target=server.run, daemon=True)
    api_thread.start()

    url = f"http://127.0.0.1:{API_PORT}"
    if not _wait_server(url) or not server.started:
        print("API 服务启动失败")
        server.should_exit = True
        sys.exit(1)

    import webview

    webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True

    bridge = NativeBridge()
    transparent = os.environ.get("CAD_UI_OPAQUE", "").lower() not in ("1", "true", "yes")

    window = webview.create_window(
        TITLE,
        url,
        js_api=bridge,
        width=1000,
        height=840,
        min_size=(860, 680),
        resizable=True,
        transparent=transparent,
        background_color="#000000" if transparent else "#070b14",
        frameless=True,
        easy_drag=False,
        shadow=True,
    )

    window.events.loaded += lambda: threading.Timer(0.6, _enable_windows_acrylic).start()
    window.events.closing += lambda *_: service.shutdown()
    webview.start(gui=_webview_gui())
    service.shutdown()
    unmount_embedded_odafc()
    os._exit(0)
