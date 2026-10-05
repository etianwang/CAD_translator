"""Reliable, shared Windows updater for Honsen applications."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.request
from ctypes import wintypes
from pathlib import Path

APP_KEY = r"Software\Honsen Program\Apps"
APP_ID = "honsen.cad-translator"
INSTALLER = re.compile(r"^Honsen_DrawTranslate_v(\d+\.\d+\.\d+)_Setup\.exe$", re.I)
RESULTS_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Honsen Program" / "UpdateResults"
WAIT_TIMEOUT_MS = 30 * 60 * 1000


class UpdateFailure(RuntimeError):
    pass


def _canonical(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(str(path))))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(target: Path) -> dict:
    try:
        data = json.loads((target / "honsen.app.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateFailure("目标目录缺少有效的 honsen.app.json") from exc
    required = ("appId", "version", "executableName", "updateRunnerName")
    if not all(isinstance(data.get(key), str) and data[key] for key in required):
        raise UpdateFailure("honsen.app.json 字段不完整")
    return data


def _registries(app_id: str) -> list[dict]:
    try:
        import winreg
        records = []
        for root, scope in ((winreg.HKEY_LOCAL_MACHINE, "HKLM"), (winreg.HKEY_CURRENT_USER, "HKCU")):
            try:
                with winreg.OpenKey(root, APP_KEY + "\\" + app_id) as key:
                    record = {name: winreg.QueryValueEx(key, name)[0] for name in ("AppId", "InstallLocation", "ExecutablePath", "Version", "UpdateRunnerPath", "UpdateManifestUrl")}
                    record["scope"] = scope
                    records.append(record)
            except OSError:
                pass
        if records:
            return records
    except OSError:
        pass
    raise UpdateFailure("未找到受信任的 Honsen Program 应用注册表记录")


def _validate_target(app_id: str, target: Path) -> tuple[dict, dict]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,127}", app_id):
        raise UpdateFailure("appId 格式无效")
    data, records = _metadata(target), _registries(app_id)
    executable = target / data["executableName"]
    runner = target / data["updateRunnerName"]
    matches = [record for record in records if _canonical(record["InstallLocation"]) == _canonical(target)]
    if not matches or any(_canonical(record["InstallLocation"]) != _canonical(target) for record in records):
        raise UpdateFailure("同一 appId 存在冲突的安装目录")
    reg = matches[0]
    if data["appId"] != app_id or reg["AppId"] != app_id:
        raise UpdateFailure("appId 与安装信息不一致")
    if _canonical(reg["InstallLocation"]) != _canonical(target) or _canonical(reg["ExecutablePath"]) != _canonical(executable) or not _canonical(reg["ExecutablePath"]).startswith(_canonical(target) + os.sep):
        raise UpdateFailure("目标目录与注册表不一致")
    if _canonical(reg["UpdateRunnerPath"]) != _canonical(runner):
        raise UpdateFailure("更新助手路径与注册表不一致")
    if not executable.is_file() or not runner.is_file():
        raise UpdateFailure("目标应用文件不完整")
    return data, reg


def _wait_for_pid(pid: int) -> None:
    if not pid:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        return  # The requested process has already exited.
    try:
        status = kernel32.WaitForSingleObject(handle, WAIT_TIMEOUT_MS)
        if status != 0:
            raise UpdateFailure("等待应用退出超时")
    finally:
        kernel32.CloseHandle(handle)


def _run_elevated(installer: Path, target: Path, log: Path) -> int:
    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND), ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR), ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY), ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]
    args = f'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="{target}" /LOG="{log}"'
    info = SHELLEXECUTEINFO(ctypes.sizeof(SHELLEXECUTEINFO), 0x00000040, None, "runas", str(installer), args, str(installer.parent), 0, None, None, None, None, 0, None, None)
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        raise UpdateFailure(f"无法以管理员权限启动安装包（Win32={ctypes.get_last_error()}）")
    try:
        if ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, WAIT_TIMEOUT_MS) != 0:
            raise UpdateFailure("安装包执行超时")
        exit_code = wintypes.DWORD()
        ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code))
        return exit_code.value
    finally:
        ctypes.windll.kernel32.CloseHandle(info.hProcess)


def _file_version(path: Path) -> str:
    size = ctypes.windll.version.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        raise UpdateFailure("新主程序缺少 Windows 文件版本")
    buffer = ctypes.create_string_buffer(size)
    if not ctypes.windll.version.GetFileVersionInfoW(str(path), 0, size, buffer):
        raise UpdateFailure("无法读取新主程序文件版本")
    value = ctypes.c_void_p()
    length = wintypes.UINT()
    if not ctypes.windll.version.VerQueryValueW(buffer, "\\", ctypes.byref(value), ctypes.byref(length)):
        raise UpdateFailure("无法查询新主程序文件版本")
    fixed = ctypes.cast(value, ctypes.POINTER(wintypes.DWORD))
    return f"{fixed[2] >> 16}.{fixed[2] & 0xffff}.{fixed[3] >> 16}"


def _write_result(app_id: str, result: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    destination = RESULTS_DIR / f"{app_id}.json"
    fd, temporary = tempfile.mkstemp(prefix=f".{app_id}.", suffix=".json", dir=RESULTS_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def _release(version: str, url: str) -> dict | None:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "HonsenUpdateRunner"})
    with urllib.request.urlopen(request, timeout=10) as response:
        release = json.loads(response.read().decode("utf-8"))
    latest = str(release.get("tag_name", "")).lstrip("v")
    if release.get("prerelease") or tuple(map(int, latest.split("."))) <= tuple(map(int, version.split("."))):
        return None
    for asset in release.get("assets", []):
        if INSTALLER.fullmatch(str(asset.get("name", ""))) and asset["name"].find(latest) >= 0 and str(asset.get("digest", "")).startswith("sha256:"):
            return {"version": latest, "url": asset["browser_download_url"], "sha256": asset["digest"][7:], "name": asset["name"]}
    raise UpdateFailure("未找到可校验的更新安装包")


def _download(update: dict) -> Path:
    directory = Path(tempfile.gettempdir()) / "Honsen Program" / "Updates"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / update["name"]
    with urllib.request.urlopen(update["url"], timeout=60) as response, path.open("wb") as stream:
        while chunk := response.read(1024 * 1024): stream.write(chunk)
    if _sha256(path).lower() != update["sha256"].lower():
        path.unlink(missing_ok=True); raise UpdateFailure("安装包 SHA-256 校验失败")
    return path


def launch(args: argparse.Namespace) -> dict:
    if args.app_id != APP_ID: raise UpdateFailure("不支持的 appId")
    records = _registries(args.app_id)
    target = Path(records[0]["InstallLocation"])
    data, reg = _validate_target(args.app_id, target)
    update = _release(reg["Version"], reg["UpdateManifestUrl"])
    if not update:
        subprocess.Popen([reg["ExecutablePath"]], cwd=str(target))
        return {"appId": args.app_id, "status": "success", "action": "launch", "fromVersion": reg["Version"], "toVersion": reg["Version"], "installLocation": str(target), "executablePath": reg["ExecutablePath"]}
    args.installer, args.sha256, args.target_dir, args.expected_version, args.restart = str(_download(update)), update["sha256"], str(target), update["version"], True
    return apply(args)


def apply(args: argparse.Namespace) -> dict:
    target, installer = Path(args.target_dir), Path(args.installer)
    log = RESULTS_DIR / f"{args.app_id}.inno.log"
    data, reg = _validate_target(args.app_id, target)
    from_version = reg["Version"]
    if _sha256(installer).lower() != args.sha256.lower():
        raise UpdateFailure("安装包 SHA-256 校验失败")
    _wait_for_pid(args.wait_pid)
    log.parent.mkdir(parents=True, exist_ok=True)
    exit_code = _run_elevated(installer, target, log)
    args.installer_exit_code = exit_code
    if exit_code != 0 or not log.is_file():
        raise UpdateFailure(f"安装包失败，退出码 {exit_code}")
    data, reg = _validate_target(args.app_id, target)
    executable = Path(reg["ExecutablePath"])
    if reg["Version"] != args.expected_version or data["version"] != args.expected_version or _file_version(executable) != args.expected_version:
        raise UpdateFailure("安装后的版本验证失败")
    if args.restart:
        subprocess.Popen([str(executable)], cwd=str(target))
    return {"appId": args.app_id, "status": "success", "source": args.source, "fromVersion": from_version, "toVersion": args.expected_version, "installLocation": str(target), "executablePath": str(executable), "installerExitCode": exit_code, "logPath": str(log), "restart": args.restart}


def _mutex(app_id: str):
    handle = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\HonsenUpdate-" + re.sub(r"[^A-Za-z0-9]", "_", app_id))
    if not handle or ctypes.get_last_error() == 183:
        raise UpdateFailure("该应用已有更新任务正在运行")
    return handle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Honsen shared update runner")
    sub = parser.add_subparsers(dest="command", required=True)
    launch_parser = sub.add_parser("launch")
    launch_parser.add_argument("--app-id", default=APP_ID)
    launch_parser.add_argument("--source", choices=("app", "toolbox"), default="app")
    launch_parser.add_argument("--wait-pid", type=int, default=0)
    launch_parser.add_argument("--relocated", action="store_true", help=argparse.SUPPRESS)
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--source", choices=("app", "toolbox"), required=True)
    apply_parser.add_argument("--app-id", required=True)
    apply_parser.add_argument("--wait-pid", type=int, required=True)
    apply_parser.add_argument("--installer", required=True)
    apply_parser.add_argument("--sha256", required=True)
    apply_parser.add_argument("--target-dir", required=True)
    apply_parser.add_argument("--expected-version", required=True)
    apply_parser.add_argument("--restart", choices=("true", "false"), required=True)
    apply_parser.add_argument("--relocated", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.restart = getattr(args, "restart", False) == "true"
    result = {"appId": args.app_id, "status": "failed", "source": args.source, "failureStep": "startup", "installerExitCode": None, "logPath": str(RESULTS_DIR / f"{args.app_id}.inno.log")}
    handle = None
    handed_off = False
    try:
        if sys.platform != "win32":
            raise UpdateFailure("HonsenUpdateRunner 仅支持 Windows")
        if not args.relocated:
            records = _registries(args.app_id); target = Path(records[0]["InstallLocation"])
            _data, registry = _validate_target(args.app_id, target)
            if _canonical(sys.executable) != _canonical(registry["UpdateRunnerPath"]):
                raise UpdateFailure("必须调用注册表登记的 HonsenUpdateRunner.exe")
            copied = Path(tempfile.gettempdir()) / "Honsen Program" / "UpdateRunner" / str(uuid.uuid4()) / "HonsenUpdateRunner.exe"
            copied.parent.mkdir(parents=True, exist_ok=False)
            copied.write_bytes(Path(sys.executable).read_bytes())
            command = [str(copied), args.command, "--source", args.source, "--app-id", args.app_id, "--wait-pid", str(args.wait_pid), "--relocated"]
            if args.command == "apply": command += ["--installer", args.installer, "--sha256", args.sha256, "--target-dir", args.target_dir, "--expected-version", args.expected_version, "--restart", "true" if args.restart else "false"]
            subprocess.Popen(command, cwd=str(copied.parent))
            handed_off = True
            return 0
        handle = _mutex(args.app_id)
        result = launch(args) if args.command == "launch" else apply(args)
    except (OSError, UpdateFailure) as exc:
        result["error"] = str(exc)
        result["installerExitCode"] = getattr(args, "installer_exit_code", None)
        if "SHA-256" in str(exc):
            result["failureStep"] = "sha256"
        elif "安装包" in str(exc):
            result["failureStep"] = "installer"
        else:
            result["failureStep"] = "validation"
    finally:
        result["completedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            if args.relocated or (result["status"] == "failed" and not handed_off):
                _write_result(args.app_id, result)
        finally:
            if handle:
                ctypes.windll.kernel32.ReleaseMutex(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
