"""Small no-network checks for persistent batch scheduling."""
import json
import tempfile
import time
from pathlib import Path

import batch_queue


with tempfile.TemporaryDirectory() as tmp:
    batch_queue.STATE_PATH = Path(tmp) / "queue.json"
    batch_queue.STATE_PATH.write_text(json.dumps({"tasks": [{"id": "old", "status": "running"}]}), encoding="utf-8")
    probe = object.__new__(batch_queue.BatchQueue)
    assert batch_queue.BatchQueue._load(probe)[0]["status"] == "queued"
    ran = []
    def run(task, log, resume_event, cancel_event):
        resume_event.wait()
        log("进度: 1/1 (100.0%)", level="INFO")
        ran.append(task["id"])
        return "out.dxf"
    q = batch_queue.BatchQueue(run, lambda _: None, lambda: "secret")
    assert q.resumable  # recovered work requires an explicit continue
    q.tasks = []
    q.pause(True)
    settings = {"output_dir": tmp, "translation_mode": "zh_to_en", "deepl_key": "secret"}
    q.add(["one.dxf", "two.dxf"], settings)
    first = q.snapshot()["tasks"][0]["id"]
    q.remove(first)
    assert len(q.snapshot()["tasks"]) == 1  # queued items can be removed
    assert "secret" not in str(q.snapshot())
    task_id = q.snapshot()["tasks"][0]["id"]
    q.pause(False)
    assert q.snapshot()["tasks"][0]["status"] == "queued" and not ran
    q.pause(True)
    assert not q.resume_event.is_set()
    q.pause(False)
    assert q.resume_event.is_set()
    q.start()
    while q.snapshot()["tasks"][0]["status"] == "running": time.sleep(.01)
    assert q.snapshot()["tasks"][0]["status"] == "succeeded"
    q.retry(task_id)
    while q.snapshot()["tasks"][0]["status"] == "running": time.sleep(.01)
    assert q.snapshot()["tasks"][0]["status"] == "succeeded"
    q.tasks[0]["status"] = "cancelled"
    replacement = {"output_dir": tmp, "translation_mode": "en_to_zh", "output_format": "dwg", "output_version": "ACAD2018", "translate_blocks": False, "deepl_key": "secret"}
    q.start(replacement)
    assert q.tasks[0]["translation_mode"] == "en_to_zh" and q.tasks[0]["output_format"] == "dwg"
    # The persisted model is allowed to contain task inputs, never the key.
    q._save()
    assert "secret" not in batch_queue.STATE_PATH.read_text(encoding="utf-8")
    q.shutdown()
    assert q.cancel_event.is_set() and not q.started
    q.clear()
    assert not q.tasks
