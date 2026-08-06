"""FastAPI backend for the React web UI."""

import asyncio
import json
import os
import queue
import sys
import threading
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cad_convert import analyze_source, dwg_unavailable_short, odafc_available, odafc_status, output_path_for
from main import CADChineseTranslator, CONFIG_PATH, output_prefix, resource_path


def _frontend_dist() -> Path:
    bundled = Path(resource_path("frontend/dist"))
    if bundled.is_dir():
        return bundled
    return Path(__file__).parent / "frontend" / "dist"


FRONTEND_DIST = _frontend_dist()
API_PORT = 8765


class ConfigBody(BaseModel):
    deepl_key: str = ""


class TranslateBody(BaseModel):
    input_file: str
    output_dir: str
    output_name: str
    translation_mode: str = "zh_to_fr"
    translate_blocks: bool = False
    deepl_key: str


class TranslationService:
    def __init__(self):
        self.status = "idle"
        self.last_message = ""
        self._log_queues: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        self._log_queues.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        if q in self._log_queues:
            self._log_queues.remove(q)

    def emit_log(self, message: str, level: str = "INFO"):
        _ = level  # 兼容 main.safe_log；UI 暂不按级别分色
        for q in list(self._log_queues):
            try:
                q.put_nowait(message)
            except queue.Full:
                pass

    def set_status(self, status: str, message: str = ""):
        self.status = status
        self.last_message = message
        payload = json.dumps({"type": "status", "status": status, "message": message}, ensure_ascii=False)
        for q in list(self._log_queues):
            try:
                q.put_nowait(f"__EVENT__:{payload}")
            except queue.Full:
                pass

    def save_config(self, deepl_key: str):
        config = {"deepl_key": deepl_key.strip()}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def load_config(self) -> dict:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"deepl_key": ""}

    @staticmethod
    def check_internet(url="http://www.baidu.com", timeout=3) -> bool:
        try:
            urllib.request.urlopen(url, timeout=timeout)
            return True
        except Exception:
            return False

    def validate(self, body: TranslateBody) -> Optional[str]:
        if not body.input_file:
            return "请选择输入文件"
        if not os.path.exists(body.input_file):
            return "输入文件不存在"
        if not body.input_file.lower().endswith((".dxf", ".dwg")):
            return "请选择 DXF 或 DWG 文件"
        if body.input_file.lower().endswith(".dwg") and not odafc_available():
            return dwg_unavailable_short()
        if not body.output_dir:
            return "请选择输出目录"
        if not os.path.exists(body.output_dir):
            return "输出目录不存在"
        if not body.output_name.strip():
            return "请输入输出文件名"
        if not body.deepl_key.strip():
            return "请配置 DeepL API Key"
        return None

    def start_translation(self, body: TranslateBody):
        with self._lock:
            if self.status == "running":
                raise HTTPException(status_code=409, detail="翻译任务正在进行中")

        err = self.validate(body)
        if err:
            raise HTTPException(status_code=400, detail=err)

        if not self.check_internet():
            raise HTTPException(status_code=503, detail="无法连接网络，请检查网络后重试")

        self.save_config(body.deepl_key)
        self.set_status("running", "翻译中...")
        self.emit_log("=" * 40)
        self.emit_log("开始翻译任务")

        def worker():
            translator = CADChineseTranslator(log_callback=self.emit_log)
            translator.deepl_api_key = body.deepl_key.strip()
            if not translator.deepl_translator:
                self.emit_log("DeepL 初始化失败，请检查 API Key")
                self.set_status("error", "DeepL 初始化失败")
                return

            try:
                meta = analyze_source(body.input_file)
                output_file = output_path_for(
                    meta, body.output_dir, body.output_name.strip()
                )
                translator.translate_cad_file(
                    body.input_file,
                    output_file,
                    body.translation_mode,
                    body.translate_blocks,
                )
                self.emit_log("=" * 40)
                self.set_status("success", "翻译完成！")
            except Exception:
                import traceback
                self.emit_log(f"ERROR: {traceback.format_exc()}")
                self.set_status("error", "翻译失败")

        threading.Thread(target=worker, daemon=True).start()


service = TranslationService()
app = FastAPI(title="CAD Translator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "status": service.status}


@app.get("/api/config")
def get_config():
    return service.load_config()


@app.post("/api/config")
def post_config(body: ConfigBody):
    service.save_config(body.deepl_key)
    return {"ok": True}


@app.get("/api/changelog")
def get_changelog():
    path = resource_path("changelog.json")
    if not os.path.exists(path):
        return {"changelog": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/status")
def get_status():
    return {"status": service.status, "message": service.last_message}


@app.get("/api/odafc-status")
def get_odafc_status():
    return odafc_status()


@app.post("/api/translate")
def start_translate(body: TranslateBody):
    service.start_translation(body)
    return {"ok": True, "status": "running"}


@app.get("/api/logs/stream")
async def stream_logs():
    q = service.subscribe()

    async def generate():
        try:
            while True:
                try:
                    msg = await asyncio.get_event_loop().run_in_executor(None, q.get, True, 1.0)
                except queue.Empty:
                    yield ": keepalive\n\n"
                    continue
                if isinstance(msg, str) and msg.startswith("__EVENT__:"):
                    yield f"data: {msg[10:]}\n\n"
                else:
                    payload = json.dumps({"type": "log", "message": str(msg)}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
        finally:
            service.unsubscribe(q)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/default-output-name")
def default_output_name(mode: str = "zh_to_fr", base: str = ""):
    prefix = output_prefix(mode)
    ts = datetime.now().strftime("%Hh%M_%d-%m-%y")
    name = f"{prefix}_{base}_{ts}" if base else f"translated_cad_{ts}"
    return {"name": name}


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        file_path = FRONTEND_DIST / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
