"""Launch FastAPI + pywebview desktop shell for the React UI."""

import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

from native_bridge import NativeBridge
from web_api import API_PORT, FRONTEND_DIST, app

TITLE = "Honsen CAD 中法互译工具"


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


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


def run_web_app():
    if not FRONTEND_DIST.exists():
        print("未找到 frontend/dist，请先构建 React 界面：")
        print("  cd frontend")
        print("  npm install")
        print("  npm run build")
        print("\n或使用旧版界面：python main.py --legacy")
        sys.exit(1)

    def start_api():
        uvicorn.run(app, host="127.0.0.1", port=API_PORT, log_level="warning")

    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    url = f"http://127.0.0.1:{API_PORT}"
    if not _wait_server(url):
        print("API 服务启动失败")
        sys.exit(1)

    import webview

    bridge = NativeBridge()
    window = webview.create_window(
        TITLE,
        url,
        js_api=bridge,
        width=980,
        height=820,
        min_size=(860, 680),
        resizable=True,
        background_color="#0a0e1a",
    )
    webview.start(gui="edgechromium")
