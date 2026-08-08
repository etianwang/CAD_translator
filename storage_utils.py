"""Small durable-write helpers shared by local application state."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


_WRITE_LOCK = threading.Lock()
_REPLACE_RETRIES = 8


def _replace_with_retry(source: str, target: Path) -> None:
    """Handle brief Windows file locks from indexing/antivirus processes."""
    for attempt in range(_REPLACE_RETRIES):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == _REPLACE_RETRIES - 1:
                raise
            time.sleep(.05 * (attempt + 1))


def atomic_write_json(path: str | Path, value: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            _replace_with_retry(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def atomic_write_bytes(path: str | Path, value: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            _replace_with_retry(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def quarantine_corrupt_file(path: str | Path) -> None:
    target = Path(path)
    if target.is_file():
        backup = target.with_name(f"{target.name}.corrupt-{int(time.time())}")
        try:
            os.replace(target, backup)
        except OSError:
            pass


@contextmanager
def atomic_output_path(path: str | Path) -> Iterator[str]:
    """Yield a same-directory temporary path and atomically publish it on success."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=target.suffix, dir=target.parent)
    os.close(fd)
    os.unlink(temporary)
    try:
        yield temporary
        _replace_with_retry(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
