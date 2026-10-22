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
PREFERENCES_DIR = RESULTS_DIR.parent / "UpdatePreferences"
GRACEFUL_EXIT_TIMEOUT_MS = 30 * 1000
INSTALL_TIMEOUT_MS = 30 * 60 * 1000


class UpdateFailure(RuntimeError):
    pass


class ProgressWindow:
    """Visible Runner progress; Inno itself remains non-interactive."""
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk.Tk(); self.tk.title("Honsen CAD 翻译器更新"); self.tk.resizable(False, False)
        self.label = ttk.Label(self.tk, text="正在检查更新…", padding=18); self.label.pack()
        self.notes = ttk.Label(self.tk, text="", justify="left", wraplength=440); self.notes.pack(padx=18, pady=(0, 10))
        self.bar = ttk.Progressbar(self.tk, length=330, mode="determinate", maximum=100); self.bar.pack(padx=18, pady=(0, 18))
        self.actions = ttk.Frame(self.tk)
        self.tk.protocol("WM_DELETE_WINDOW", lambda: None); self.tk.update()

    def set(self, text: str, percent: int | None = None, notes: str | None = None):
        self.label.configure(text=text)
        if notes is not None: self.notes.configure(text=notes[:1200])
        if percent is None: self.bar.configure(mode="indeterminate"); self.bar.start(12)
        else: self.bar.stop(); self.bar.configure(mode="determinate", value=percent)
        self.tk.update_idletasks(); self.tk.update()

    def close(self):
        self.tk.destroy()

    def choose(self, version: str, notes: str) -> str:
        import tkinter as tk
        from tkinter import ttk

        self.set(f"发现 v{version}", 0, notes or "本版本未提供更新说明。")
        choice = tk.StringVar(master=self.tk, value="")
        self.actions.pack(pady=(0, 18))
        ttk.Button(self.actions, text="立即更新", command=lambda: choice.set("update")).pack(side="left", padx=4)
        ttk.Button(self.actions, text="稍后提醒", command=lambda: choice.set("later")).pack(side="left", padx=4)
        ttk.Button(self.actions, text="跳过此版本", command=lambda: choice.set("skip")).pack(side="left", padx=4)
        self.tk.protocol("WM_DELETE_WINDOW", lambda: choice.set("later"))
        self.tk.wait_variable(choice)
        self.actions.pack_forget()
        for button in self.actions.winfo_children(): button.destroy()
        self.tk.protocol("WM_DELETE_WINDOW", lambda: None)
        return choice.get()


def _canonical(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(str(path))))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(target: Path) -> dict:
    manifest = target / "honsen.app.json"
    if manifest.resolve().parent != target.resolve():
        raise UpdateFailure("Manifest 链接超出安装目录")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateFailure("目标目录缺少有效的 honsen.app.json") from exc
    executable = data.get("executable") or data.get("executableName")
    runner = data.get("updateRunner") or data.get("updateRunnerName")
    if not all(isinstance(data.get(key), str) and data[key] for key in ("appId", "version")) or not all(isinstance(value, str) and value for value in (executable, runner)):
        raise UpdateFailure("honsen.app.json 字段不完整")
    if "updateManifestUrl" in data and (not isinstance(data["updateManifestUrl"], str) or not data["updateManifestUrl"]):
        raise UpdateFailure("honsen.app.json 的 updateManifestUrl 无效")
    if "schemaVersion" in data and data["schemaVersion"] != 1:
        raise UpdateFailure("不支持的 honsen.app.json schemaVersion")
    if data.get("schemaVersion") == 1 and not all(isinstance(data.get(key), str) and data[key] for key in ("displayName", "publisher", "updateManifestUrl")):
        raise UpdateFailure("标准 honsen.app.json 字段不完整")
    if any(not re.fullmatch(r'[^\\/:*?"<>|]+\.exe', value, re.I) or ".." in value for value in (executable, runner)):
        raise UpdateFailure("Manifest 可执行文件名无效")
    if runner != "HonsenUpdateRunner.exe":
        raise UpdateFailure("Manifest Runner 名称无效")
    data["executable"] = executable
    data["updateRunner"] = runner
    return data


def _registries(app_id: str) -> list[dict]:
    import winreg
    records = []
    for root, scope in ((winreg.HKEY_LOCAL_MACHINE, "HKLM"), (winreg.HKEY_CURRENT_USER, "HKCU")):
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                key = winreg.OpenKey(root, APP_KEY + "\\" + app_id, 0, winreg.KEY_READ | view)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise UpdateFailure("无法读取应用注册表视图") from exc
            with key:
                try:
                    record = {name: winreg.QueryValueEx(key, name)[0] for name in ("AppId", "InstallLocation", "ExecutablePath", "Version", "Publisher", "LauncherPath", "UpdateRunnerPath", "UpdateManifestUrl")}
                except OSError as exc:
                    raise UpdateFailure("应用注册表登记不完整") from exc
                record["scope"] = scope
                records.append(record)
    if not records:
        raise UpdateFailure("未找到受信任的 Honsen Program 应用注册表记录")
    return records


def _validate_target(app_id: str, target: Path) -> tuple[dict, dict]:
    if app_id != APP_ID:
        raise UpdateFailure("appId 格式无效")
    data, records = _metadata(target), _registries(app_id)
    executable = target / data["executable"]
    runner = target / data["updateRunner"]
    matches = [record for record in records if _canonical(record["InstallLocation"]) == _canonical(target)]
    if not matches or any(_canonical(record["InstallLocation"]) != _canonical(target) for record in records):
        raise UpdateFailure("同一 appId 存在冲突的安装目录")
    reg = matches[0]
    for other in records[1:]:
        if any(other[key] != reg[key] for key in ("AppId", "Version", "Publisher", "UpdateManifestUrl")) or any(
            _canonical(other[key]) != _canonical(reg[key]) for key in ("ExecutablePath", "LauncherPath", "UpdateRunnerPath")
        ):
            raise UpdateFailure("同一 appId 的登记内容冲突")
    if data["appId"] != app_id or reg["AppId"] != app_id:
        raise UpdateFailure("appId 与安装信息不一致")
    if _canonical(reg["InstallLocation"]) != _canonical(target) or _canonical(reg["ExecutablePath"]) != _canonical(executable) or not _canonical(reg["ExecutablePath"]).startswith(_canonical(target) + os.sep):
        raise UpdateFailure("目标目录与注册表不一致")
    if _canonical(reg["UpdateRunnerPath"]) != _canonical(runner) or _canonical(reg["LauncherPath"]) != _canonical(runner):
        raise UpdateFailure("更新助手路径与注册表不一致")
    if data.get("updateManifestUrl") and data["updateManifestUrl"] != reg["UpdateManifestUrl"]:
        raise UpdateFailure("更新源与注册表不一致")
    if data["version"] != reg["Version"]:
        raise UpdateFailure("Manifest 与登记版本不一致")
    if data.get("publisher") and data["publisher"] != reg["Publisher"]:
        raise UpdateFailure("发布者与注册表不一致")
    if not target.is_absolute() or not executable.is_file() or not runner.is_file():
        raise UpdateFailure("目标应用文件不完整")
    if executable.resolve().parent != target.resolve() or runner.resolve().parent != target.resolve():
        raise UpdateFailure("可执行文件链接超出安装目录")
    return data, reg


def _process_path(handle) -> str:
    size = wintypes.DWORD(32768); buffer = ctypes.create_unicode_buffer(size.value)
    query = ctypes.WinDLL("kernel32", use_last_error=True).QueryFullProcessImageNameW
    query.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    if not query(handle, 0, buffer, ctypes.byref(size)):
        raise UpdateFailure("无法验证待退出进程路径")
    return buffer.value


def _wait_for_pid(pid: int, expected_executable: Path) -> None:
    if pid == 0:
        return
    if pid < 0:
        raise UpdateFailure("进程 PID 无效")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(0x00100000 | 0x0400 | 0x0001, False, pid)  # SYNCHRONIZE|QUERY_INFORMATION|TERMINATE
    if not handle:
        if ctypes.get_last_error() == 87:
            return
        raise UpdateFailure("无法打开待退出进程")
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    try:
        if _canonical(_process_path(handle)) != _canonical(expected_executable):
            raise UpdateFailure("待退出进程路径不匹配")
        status = kernel32.WaitForSingleObject(handle, GRACEFUL_EXIT_TIMEOUT_MS)
        if status == 0: return
        if status != 258: raise UpdateFailure("等待应用退出失败")
        if _canonical(_process_path(handle)) != _canonical(expected_executable):
            raise UpdateFailure("拒绝终止路径不匹配的进程")
        if not kernel32.TerminateProcess(handle, 1):
            raise UpdateFailure("无法终止仍在运行的主程序")
        if kernel32.WaitForSingleObject(handle, GRACEFUL_EXIT_TIMEOUT_MS) != 0:
            raise UpdateFailure("主程序终止后仍未退出")
    finally:
        kernel32.CloseHandle(handle)


def _run_elevated(installer: Path, target: Path, log: Path) -> int:
    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND), ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR), ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY), ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]
    args = f'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR="{target}" /LOG="{log}"'
    info = SHELLEXECUTEINFO(ctypes.sizeof(SHELLEXECUTEINFO), 0x00000040, None, "runas", str(installer), args, str(installer.parent), 0, None, None, None, None, 0, None, None)
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        raise UpdateFailure(f"无法以管理员权限启动安装包（Win32={ctypes.get_last_error()}）")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    try:
        if kernel32.WaitForSingleObject(info.hProcess, INSTALL_TIMEOUT_MS) != 0:
            raise UpdateFailure("安装包执行超时")
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
            raise UpdateFailure("无法读取安装程序退出码")
        return exit_code.value
    finally:
        kernel32.CloseHandle(info.hProcess)


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


def _result_location(app_id: str, operation_id: str | None, supplied_path: str | None) -> tuple[str, Path]:
    if app_id != APP_ID:
        raise UpdateFailure("不支持的 appId")
    try:
        operation_id = str(uuid.UUID(operation_id)) if operation_id else str(uuid.uuid4())
    except (TypeError, ValueError) as exc:
        raise UpdateFailure("operationId 必须是 GUID") from exc
    destination = RESULTS_DIR / app_id / f"{operation_id}.json"
    if supplied_path and (not Path(supplied_path).is_absolute() or _canonical(supplied_path) != _canonical(destination)):
        raise UpdateFailure("result-path 必须是该 operationId 的受信任结果路径")
    return operation_id, destination


def _result(args: argparse.Namespace, status: str, **values) -> dict:
    result = {
        "appId": args.app_id, "status": status, "source": args.source,
        "operationId": args.operation_id, "fromVersion": None, "toVersion": None,
        "step": None, "installerExitCode": None, "installerLogPath": None,
        "message": None,
    }
    result.update(values)
    return result


def _claim_operation(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.parent.resolve().parent != RESULTS_DIR.resolve():
        raise UpdateFailure("结果目录链接超出允许范围")
    if destination.exists():
        raise UpdateFailure("operationId 已被使用")
    try:
        fd = os.open(str(destination.with_suffix(".claim")), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except FileExistsError as exc:
        raise UpdateFailure("operationId 已被使用") from exc


def _write_result(destination: Path, result: dict) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.stem}.", suffix=".json", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        os.link(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def _skipped_version(app_id: str) -> str:
    try: return str(json.loads((PREFERENCES_DIR / f"{app_id}.json").read_text(encoding="utf-8")).get("skipVersion", ""))
    except (OSError, ValueError): return ""


def _skip_version(app_id: str, version: str) -> None:
    PREFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    (PREFERENCES_DIR / f"{app_id}.json").write_text(json.dumps({"skipVersion": version}), encoding="utf-8")


def _release(version: str, url: str) -> dict | None:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "HonsenUpdateRunner"})
    with urllib.request.urlopen(request, timeout=10) as response:
        release = json.loads(response.read().decode("utf-8"))
    latest = str(release.get("tag_name", "")).lstrip("v")
    if release.get("prerelease") or tuple(map(int, latest.split("."))) <= tuple(map(int, version.split("."))):
        return None
    for asset in release.get("assets", []):
        match = INSTALLER.fullmatch(str(asset.get("name", "")))
        if match and match.group(1) == latest and re.fullmatch(r"sha256:[0-9a-fA-F]{64}", str(asset.get("digest", ""))) and str(asset.get("browser_download_url", "")).startswith("https://"):
            return {"version": latest, "url": asset["browser_download_url"], "sha256": asset["digest"][7:], "name": asset["name"], "notes": str(release.get("body", ""))}
    raise UpdateFailure("未找到可校验的更新安装包")


def _download(update: dict, ui: ProgressWindow | None = None) -> Path:
    directory = Path(tempfile.gettempdir()) / "Honsen Program" / "Updates"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / update["name"]
    with urllib.request.urlopen(update["url"], timeout=60) as response, path.open("wb") as stream:
        total = int(response.headers.get("Content-Length", 0)); received = 0
        while chunk := response.read(1024 * 1024):
            stream.write(chunk); received += len(chunk)
            if ui: ui.set(f"正在下载更新… {received * 100 // total if total else 0}%", received * 100 // total if total else None)
    if _sha256(path).lower() != update["sha256"].lower():
        path.unlink(missing_ok=True); raise UpdateFailure("安装包 SHA-256 校验失败")
    return path


def launch(args: argparse.Namespace, ui: ProgressWindow | None = None) -> dict:
    if args.app_id != APP_ID: raise UpdateFailure("不支持的 appId")
    records = _registries(args.app_id)
    target = Path(records[0]["InstallLocation"])
    data, reg = _validate_target(args.app_id, target)
    if ui: ui.set("正在检查更新…", None)
    update = _release(reg["Version"], reg["UpdateManifestUrl"])
    if not update:
        subprocess.Popen([reg["ExecutablePath"]], cwd=str(target))
        return _result(args, "success", fromVersion=reg["Version"], toVersion=reg["Version"], message="已启动当前版本")
    if _skipped_version(args.app_id) == update["version"]:
        subprocess.Popen([reg["ExecutablePath"]], cwd=str(target))
        return _result(args, "success", fromVersion=reg["Version"], toVersion=reg["Version"], message="已跳过此版本")
    choice = ui.choose(update["version"], update["notes"]) if ui else "update"
    if choice != "update":
        if choice == "skip": _skip_version(args.app_id, update["version"])
        subprocess.Popen([reg["ExecutablePath"]], cwd=str(target))
        return _result(args, "success", fromVersion=reg["Version"], toVersion=reg["Version"], message="稍后提醒" if choice == "later" else "已跳过此版本")
    args.installer, args.sha256, args.target_dir, args.expected_version, args.restart = str(_download(update, ui)), update["sha256"], str(target), update["version"], True
    return apply(args, ui)


def apply(args: argparse.Namespace, ui: ProgressWindow | None = None) -> dict:
    target, installer = Path(args.target_dir), Path(args.installer)
    if not target.is_absolute() or not installer.is_absolute() or not re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.expected_version):
        raise UpdateFailure("更新参数无效")
    log = Path(args.result_path).with_suffix(".inno.log")
    args.installer_log_path = str(log)
    data, reg = _validate_target(args.app_id, target)
    from_version = reg["Version"]
    if _sha256(installer).lower() != args.sha256.lower():
        raise UpdateFailure("安装包 SHA-256 校验失败")
    if ui: ui.set("正在等待应用退出…", None)
    _wait_for_pid(args.wait_pid, Path(reg["ExecutablePath"]))
    log.parent.mkdir(parents=True, exist_ok=True)
    if ui: ui.set("正在安装更新…", None)
    exit_code = _run_elevated(installer, target, log)
    args.installer_exit_code = exit_code
    if exit_code != 0 or not log.is_file():
        raise UpdateFailure(f"安装包失败，退出码 {exit_code}")
    if ui: ui.set("正在验证新版本…", None)
    data, reg = _validate_target(args.app_id, target)
    executable = Path(reg["ExecutablePath"])
    if reg["Version"] != args.expected_version or data["version"] != args.expected_version or _file_version(executable) != args.expected_version:
        raise UpdateFailure("安装后的版本验证失败")
    return _result(args, "success", fromVersion=from_version, toVersion=args.expected_version, installerExitCode=exit_code, installerLogPath=str(log), installLocation=str(target), executablePath=str(executable), message="更新完成")


def _validate_relocated(executable: Path, registered: Path) -> None:
    expected_root = (Path(tempfile.gettempdir()) / "Honsen Program" / "UpdateRunner").resolve()
    actual = executable.resolve()
    if actual.name != "HonsenUpdateRunner.exe" or actual.parent.parent != expected_root or _sha256(actual) != _sha256(registered):
        raise UpdateFailure("临时 Runner 身份不一致")


def _mutex(app_id: str):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.CreateMutexW(None, True, "Global\\HonsenUpdate-" + re.sub(r"[^A-Za-z0-9]", "_", app_id))
    if not handle:
        raise UpdateFailure("无法创建更新互斥锁")
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        raise UpdateFailure("该应用已有更新任务正在运行")
    return handle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Honsen shared update runner")
    sub = parser.add_subparsers(dest="command", required=True)
    launch_parser = sub.add_parser("launch")
    launch_parser.add_argument("--app-id", default=APP_ID)
    launch_parser.add_argument("--source", choices=("app", "toolbox"), default="app")
    launch_parser.add_argument("--wait-pid", type=int, default=0)
    launch_parser.add_argument("--operation-id")
    launch_parser.add_argument("--result-path")
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
    apply_parser.add_argument("--operation-id", required=True)
    apply_parser.add_argument("--result-path", required=True)
    apply_parser.add_argument("--relocated", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.app_id != APP_ID:
        return 1
    args.restart = getattr(args, "restart", False) == "true"
    try:
        args.operation_id, args.result_path = _result_location(args.app_id, args.operation_id, args.result_path)
    except UpdateFailure:
        return 1
    if not args.relocated:
        try:
            _claim_operation(Path(args.result_path))
        except (OSError, UpdateFailure):
            return 1
    result = _result(args, "failed", step="startup")
    handle = None
    handed_off = False
    ui = None
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
            command = [str(copied), args.command, "--source", args.source, "--app-id", args.app_id, "--wait-pid", str(args.wait_pid), "--operation-id", args.operation_id, "--result-path", str(args.result_path), "--relocated"]
            if args.command == "apply": command += ["--installer", args.installer, "--sha256", args.sha256, "--target-dir", args.target_dir, "--expected-version", args.expected_version, "--restart", "true" if args.restart else "false"]
            subprocess.Popen(command, cwd=str(copied.parent))
            handed_off = True
            return 0
        records = _registries(args.app_id)
        _data, registry = _validate_target(args.app_id, Path(records[0]["InstallLocation"]))
        _validate_relocated(Path(sys.executable), Path(registry["UpdateRunnerPath"]))
        if not Path(args.result_path).with_suffix(".claim").is_file():
            raise UpdateFailure("操作标记缺失")
        handle = _mutex(args.app_id)
        ui = ProgressWindow()
        result = launch(args, ui) if args.command == "launch" else apply(args, ui)
    except (OSError, UpdateFailure) as exc:
        result["message"] = str(exc)
        result["installerExitCode"] = getattr(args, "installer_exit_code", None)
        result["installerLogPath"] = getattr(args, "installer_log_path", None)
        if "SHA-256" in str(exc):
            result["step"] = "sha256"
        elif "安装包" in str(exc):
            result["step"] = "installer"
        else:
            result["step"] = "validation"
    finally:
        if ui: ui.close()
        result["completedAtUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            if args.relocated or (result["status"] == "failed" and not handed_off):
                _write_result(Path(args.result_path), result)
        finally:
            if handle:
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
                kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
                kernel32.ReleaseMutex(handle)
                kernel32.CloseHandle(handle)
    if result["status"] == "success" and args.restart and result.get("executablePath"):
        try:
            subprocess.Popen([result["executablePath"]], cwd=result["installLocation"])
        except OSError:
            return 1
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
