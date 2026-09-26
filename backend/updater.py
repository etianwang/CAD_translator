"""GitHub Release checks and verified Windows update downloads."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path


CURRENT_VERSION = "1.9.4"
RELEASE_API_URL = "https://api.github.com/repos/etianwang/CAD_translator/releases/latest"
UPDATE_DIR = Path(tempfile.gettempdir()) / "Honsen CAD Translator Updates"
_INSTALLER = re.compile(r"^Honsen_DrawTranslate_v(\d+\.\d+\.\d+)_Setup\.exe$", re.IGNORECASE)
_STANDALONE = re.compile(r"^HonsenCAD\.v(\d+\.\d+\.\d+)\.exe$", re.IGNORECASE)


class UpdateError(RuntimeError):
    """The release feed or its update asset could not be safely used."""


def _version(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    if not match:
        raise UpdateError("发布版本号格式无效")
    return tuple(map(int, match.groups()))


def _request(url: str):
    return urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"HonsenCADTranslator/{CURRENT_VERSION}"},
    )


def check_for_update() -> dict:
    """Return only a newer release with a checksummed Windows update asset."""
    try:
        with urllib.request.urlopen(_request(RELEASE_API_URL), timeout=8) as response:
            release = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"available": False, "current_version": CURRENT_VERSION, "message": f"检查更新失败：{exc}"}

    try:
        latest = str(release["tag_name"]).lstrip("v")
        if release.get("prerelease") or _version(latest) <= _version(CURRENT_VERSION):
            return {"available": False, "current_version": CURRENT_VERSION, "latest_version": latest, "message": "已是最新版本"}
        asset_type, asset = next(
            ((kind, item) for kind, pattern in (("installer", _INSTALLER), ("installer", _STANDALONE))
             for item in release.get("assets", [])
             if (match := pattern.fullmatch(str(item.get("name", "")))) and match.group(1) == latest),
            ("", None),
        )
        digest = str(asset.get("digest", "")) if asset else ""
        if not asset or not digest.startswith("sha256:") or not asset.get("browser_download_url"):
            raise UpdateError("新版未附带可校验的 Windows 更新包")
    except (KeyError, UpdateError) as exc:
        return {"available": False, "current_version": CURRENT_VERSION, "message": str(exc)}

    return {
        "available": True,
        "current_version": CURRENT_VERSION,
        "latest_version": latest,
        "release_url": release.get("html_url", ""),
        "notes": release.get("body", ""),
        "asset_url": asset["browser_download_url"],
        "asset_name": asset["name"],
        "asset_type": asset_type,
        "sha256": digest.removeprefix("sha256:"),
    }


def download_update() -> dict:
    """Download a verified update asset to a safe temporary location."""
    update = check_for_update()
    if not update["available"]:
        raise UpdateError(update["message"])

    target = UPDATE_DIR / update["asset_name"]
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".download-", suffix=".exe", dir=UPDATE_DIR)
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as stream, urllib.request.urlopen(_request(update["asset_url"]), timeout=60) as response:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                stream.write(chunk)
        if digest.hexdigest().lower() != update["sha256"].lower():
            raise UpdateError("更新包 SHA-256 校验失败，已拒绝安装")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"version": update["latest_version"], "installer_path": str(target), "asset_type": update["asset_type"]}
