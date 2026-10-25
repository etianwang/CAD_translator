"""No-network checks for release selection and installer integrity."""

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import updater
from desktop.native_bridge import NativeBridge
from desktop import update_runner


def release(version="1.11.13", *, digest=True, prerelease=False, name=None):
    asset_name = name or f"Honsen_DrawTranslate_v{version}_Setup.exe"
    payload = b"installer"
    return {
        "tag_name": f"v{version}",
        "prerelease": prerelease,
        "html_url": "https://example.test/release",
        "body": "release notes",
        "assets": [{
            "name": asset_name,
            "browser_download_url": "https://example.test/installer.exe",
            **({"digest": f"sha256:{hashlib.sha256(payload).hexdigest()}"} if digest else {}),
        }],
    }


class UpdaterTests(unittest.TestCase):
    def test_runner_update_choice_buttons_work_in_one_window(self):
        import tkinter
        try:
            window = update_runner.ProgressWindow()
        except tkinter.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        window.tk.withdraw()
        try:
            for index, expected in enumerate(("update", "later", "skip")):
                with self.subTest(choice=expected):
                    def invoke_when_ready(i=index):
                        buttons = window.actions.winfo_children()
                        if len(buttons) == 3:
                            buttons[i].invoke()
                        else:
                            window.tk.after(10, invoke_when_ready)
                    timeout = window.tk.after(5000, window.tk.destroy)
                    window.tk.after(10, invoke_when_ready)
                    self.assertEqual(window.choose("1.11.9", "notes"), expected)
                    window.tk.after_cancel(timeout)
                    self.assertFalse(window.actions.winfo_children())
        finally:
            window.close()

    def test_only_newer_checksums_installer_is_offered(self):
        with patch("backend.updater.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release()).encode())):
            update = updater.check_for_update()
        self.assertTrue(update["available"])
        self.assertEqual(update["latest_version"], "1.11.13")

    def test_invalid_or_non_newer_releases_are_refused(self):
        for payload in (
            release("1.9.4"),
            release("1.9.8"),
            release("1.11.13", prerelease=True),
            release("1.11.13", digest=False),
            release("1.11.1", name="HonsenCAD.v1.9.exe"),
        ):
            with self.subTest(payload=payload), patch("backend.updater.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
                self.assertFalse(updater.check_for_update()["available"])

    def test_download_requires_matching_sha256(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(updater, "UPDATE_DIR", Path(directory)):
            metadata = io.BytesIO(json.dumps(release()).encode())
            with patch("backend.updater.urllib.request.urlopen", side_effect=[metadata, io.BytesIO(b"installer")]):
                result = updater.download_update()
            self.assertEqual(Path(result["installer_path"]).read_bytes(), b"installer")

            metadata = io.BytesIO(json.dumps(release()).encode())
            with patch("backend.updater.urllib.request.urlopen", side_effect=[metadata, io.BytesIO(b"tampered")]):
                with self.assertRaises(updater.UpdateError):
                    updater.download_update()
            self.assertFalse(list(Path(directory).glob(".download-*")))

    def test_windows_launches_only_the_installed_shared_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            app_dir.mkdir()
            executable = app_dir / "Honsen DrawTranslate.exe"
            executable.write_bytes(b"app")
            runner = app_dir / "HonsenUpdateRunner.exe"
            runner.write_bytes(b"runner")
            (app_dir / "honsen.app.json").write_text(json.dumps({
                "appId": "honsen.cad-translator", "version": "1.10.0",
                "schemaVersion": 1, "executable": executable.name, "updateRunner": runner.name,
                "displayName": "Honsen CAD 翻译器", "publisher": "Honsen",
                "updateManifestUrl": "https://example.test/latest",
                "executableName": executable.name, "updateRunnerName": runner.name,
            }), encoding="utf-8")
            installer = Path(directory) / "HonsenCAD.v1.9.4.exe"
            installer.write_bytes(b"installer")
            with (
                patch("desktop.native_bridge.sys.platform", "win32"),
                patch("desktop.native_bridge.sys.executable", str(executable)),
                patch("desktop.native_bridge.subprocess.Popen") as popen,
                patch("desktop.native_bridge.threading.Thread") as thread,
            ):
                result = NativeBridge().install_update(str(installer), "a" * 64, "1.10.1")
            self.assertTrue(result["ok"])
            self.assertRegex(result["operationId"], r"^[0-9a-f-]{36}$")
            self.assertTrue(result["resultPath"].endswith(result["operationId"] + ".json"))
            command = popen.call_args.args[0]
            self.assertEqual(Path(command[0]).resolve(), runner.resolve())
            self.assertEqual(command[1:3], ["apply", "--source"])
            self.assertIn("--wait-pid", command)
            self.assertEqual(Path(command[command.index("--target-dir") + 1]).resolve(), app_dir.resolve())
            self.assertEqual(command[command.index("--operation-id") + 1], result["operationId"])
            self.assertEqual(command[command.index("--result-path") + 1], result["resultPath"])
            thread.assert_called_once()

        self.assertIn("更新助手", NativeBridge().install_update("missing.exe", "", "")["error"])

    def test_existing_honsencad_installer_name_is_accepted(self):
        with patch("backend.updater.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release(name="HonsenCAD.v1.11.13.exe")).encode())):
            self.assertTrue(updater.check_for_update()["available"])

    def test_inno_setup_leaves_silent_restart_to_the_shared_runner(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        run_line = next(line for line in script.splitlines() if line.startswith('Filename: "{app}\\{#MyAppExeName}"; Description:'))
        self.assertIn("runasoriginaluser", run_line)
        self.assertIn("postinstall", run_line)
        self.assertNotIn("skipifsilent", run_line)

    def test_inno_setup_never_rewrites_user_shortcuts(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        self.assertIn('Source: "..\\dist\\Honsen DrawTranslate.exe"', script)
        self.assertNotIn('Name: "{app}\\Honsen DrawTranslate v*.exe"', script)
        self.assertNotIn('Name: "{app}\\Honsen_CAD_Translator_v*.exe"', script)
        self.assertNotIn("cscript.exe", script.lower())
        self.assertNotIn("migrate_shortcuts", script.lower())
        self.assertIn('#define MyShortcutName "Honsen CAD 翻译器"', script)
        self.assertIn('Name: "{autodesktop}\\{#MyShortcutName}"', script)

    def test_inno_setup_registers_the_fixed_honsen_program_identity(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        registry_key = 'HKLM; Subkey: "Software\\Honsen Program\\Apps\\{#MyHonsenAppId}"'
        self.assertIn('#define MyHonsenAppId "honsen.cad-translator"', script)
        self.assertIn(registry_key, script)
        self.assertIn('ValueName: "InstallLocation"; ValueData: "{app}"', script)
        self.assertIn('ValueName: "ExecutablePath"; ValueData: "{app}\\{#MyAppExeName}"', script)
        self.assertIn('ValueName: "UpdateRunnerPath"; ValueData: "{app}\\HonsenUpdateRunner.exe"', script)
        self.assertIn('ExistingInstallLocation := ReadExistingInstallLocation()', script)
        self.assertIn('只能更新原目录', script)
        self.assertIn('ValueName: "Version"; ValueData: "{#MyAppVersion}"', script)
        self.assertIn('ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"', script)
        self.assertIn('ValueName: "UpdateUrl"; ValueData: "{#MyHonsenUpdateURL}"', script)
        self.assertIn('ValueData: "{#MyHonsenAppId}"; Flags: uninsdeletekey', script)

    def test_uninstall_never_recursively_deletes_install_directory(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        self.assertNotIn('Type: filesandordirs; Name: "{app}"', script)
        self.assertNotIn('[UninstallDelete]', script)

    def test_installer_checks_all_registry_views_and_rejects_conflicts(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        for root in ("HKLM32", "HKLM64", "HKCU32", "HKCU64"):
            self.assertIn("CheckExistingRegistration(" + root, script)
        self.assertIn("ExistingRegistrationError", script)
        self.assertIn("RegKeyExists", script)

    def test_installer_requires_absolute_recorded_location_and_executable(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        self.assertIn("ExtractFileDrive(Location) = ''", script)
        self.assertIn("not RegQueryStringValue(RootKey, 'Software\\Honsen Program\\Apps\\{#MyHonsenAppId}', 'ExecutablePath', ExecutablePath)", script)
        self.assertIn("FileExists(ExecutablePath)", script)

    def test_installer_shortcuts_and_machine_scope_follow_contract(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        self.assertIn('ValueName: "InstallScope"; ValueData: "machine"', script)
        shortcuts = [line for line in script.splitlines() if 'Filename: "{app}\\HonsenUpdateRunner.exe"' in line]
        self.assertEqual(len(shortcuts), 2)
        for line in shortcuts:
            self.assertIn('Parameters: "launch --app-id {#MyHonsenAppId} --source app"', line)

    def test_release_version_gate_rejects_mismatch(self):
        from installer.release_check import validate_versions
        versions = {"manifest": "1.2.3", "installer": "1.2.3", "exe": "1.2.3", "tag": "v1.2.3", "asset": "Honsen_DrawTranslate_v1.2.3_Setup.exe"}
        validate_versions(versions)
        for field, bad in (("installer", "1.2.4"), ("exe", "1.2.4"), ("tag", "v1.2.4"), ("asset", "Honsen_DrawTranslate_v1.2.4_Setup.exe"), ("frontend", "1.2.4"), ("product", "1.2.4")):
            versions.setdefault("frontend", "1.2.3")
            versions.setdefault("product", "1.2.3")
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_versions({**versions, field: bad})

    def test_setup_version_accepts_only_zero_fourth_component(self):
        from installer.release_check import normalize_setup_version
        self.assertEqual(normalize_setup_version("1.11.10.0   "), "1.11.10")
        with self.assertRaises(ValueError):
            normalize_setup_version("1.11.10.1")
        with self.assertRaises(ValueError):
            normalize_setup_version("1.11.10.0.0")

    def test_release_gate_rejects_digest_and_asset_disagreement(self):
        from installer.release_check import validate_release
        payload = release("1.11.11")
        asset = payload["assets"][0]
        payload["assets"].append({"name": asset["name"] + ".sha256"})
        digest = asset["digest"][7:]
        validate_release(payload, "1.11.11", digest)
        with self.assertRaises(ValueError):
            validate_release(payload, "1.11.11", "0" * 64)
        with self.assertRaises(ValueError):
            validate_release({**payload, "assets": [asset]}, "1.11.11", digest)

    def test_release_build_creates_sha256_sidecar(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "build_installer.ps1").read_text(encoding="utf-8")
        self.assertIn('Get-FileHash -LiteralPath $setup -Algorithm SHA256', script)
        self.assertIn('$setup + ".sha256"', script)

    def test_runner_and_manifest_are_packaged_and_runner_receives_checksum(self):
        root = Path(__file__).resolve().parents[1]
        spec = (root / "Honsen_CAD_Translator_v1.10.1.spec").read_text(encoding="utf-8")
        installer = (root / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        bridge = (root / "desktop" / "native_bridge.py").read_text(encoding="utf-8")
        manifest = json.loads((root / "honsen.app.json").read_text(encoding="utf-8"))
        self.assertIn('"honsen.app.json"', spec)
        self.assertIn('Source: "..\\dist\\HonsenUpdateRunner.exe"', installer)
        self.assertIn('Source: "..\\honsen.app.json"', installer)
        self.assertEqual(manifest["appId"], "honsen.cad-translator")
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["executable"], "Honsen DrawTranslate.exe")
        self.assertEqual(manifest["updateRunner"], "HonsenUpdateRunner.exe")
        self.assertTrue(manifest["displayName"])
        self.assertEqual(manifest["publisher"], "Honsen")
        self.assertIn('"--sha256", sha256', bridge)
        runner = (root / "desktop" / "update_runner.py").read_text(encoding="utf-8")
        self.assertIn('"Honsen Program" / "UpdateRunner"', runner)
        self.assertIn('"--relocated"', runner)
        self.assertIn('_result(args, "success"', runner)

    def test_toolbox_launch_uses_registered_executable_without_update(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            executable = target / "Honsen DrawTranslate.exe"
            record = {"InstallLocation": str(target), "ExecutablePath": str(executable), "Version": "1.0.0", "UpdateManifestUrl": "https://example.test/latest"}
            args = SimpleNamespace(app_id=update_runner.APP_ID, source="toolbox", operation_id="123")
            with patch.object(update_runner, "_registries", return_value=[record]), patch.object(update_runner, "_validate_target", return_value=({}, record)), patch.object(update_runner, "_release", return_value=None), patch("desktop.update_runner.subprocess.Popen") as popen:
                result = update_runner.launch(args)
            self.assertEqual(result["status"], "success")
            popen.assert_called_once_with([str(executable)], cwd=str(target))

    def test_app_update_requires_matching_hash_and_verified_installed_version(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installer = root / "setup.exe"
            installer.write_bytes(b"setup")
            executable = root / "Honsen DrawTranslate.exe"
            old = {"ExecutablePath": str(executable), "Version": "1.0.0"}
            new = {**old, "Version": "1.1.0"}
            args = SimpleNamespace(app_id=update_runner.APP_ID, source="app", operation_id="123", target_dir=str(root), installer=str(installer), result_path=str(root / "123.json"), sha256=hashlib.sha256(b"setup").hexdigest(), wait_pid=0, expected_version="1.1.0", restart=True)
            def install(_installer, _target, log):
                log.write_text("ok", encoding="utf-8")
                return 0
            with patch.object(update_runner, "_validate_target", side_effect=[({"version": "1.0.0"}, old), ({"version": "1.1.0"}, new)]), patch.object(update_runner, "_wait_for_pid"), patch.object(update_runner, "_run_elevated", side_effect=install), patch.object(update_runner, "_file_version", return_value="1.1.0"), patch("desktop.update_runner.subprocess.Popen") as popen:
                result = update_runner.apply(args)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["executablePath"], str(executable))
            popen.assert_not_called()
            args.sha256 = "0" * 64
            with patch.object(update_runner, "_validate_target", return_value=({"version": "1.0.0"}, old)), patch.object(update_runner, "_run_elevated") as run:
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner.apply(args)
            run.assert_not_called()
            args.sha256 = hashlib.sha256(b"setup").hexdigest()
            with patch.object(update_runner, "_validate_target", return_value=({"version": "1.0.0"}, old)), patch.object(update_runner, "_wait_for_pid"), patch.object(update_runner, "_run_elevated", return_value=5), patch("desktop.update_runner.subprocess.Popen") as popen:
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner.apply(args)
            popen.assert_not_called()

    def test_runner_rejects_mismatched_registry_or_manifest_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            executable = target / "Honsen DrawTranslate.exe"
            runner = target / "HonsenUpdateRunner.exe"
            executable.write_bytes(b"app")
            runner.write_bytes(b"runner")
            (target / "honsen.app.json").write_text(json.dumps({
                "appId": "honsen.cad-translator", "version": "1.10.0",
                "schemaVersion": 1, "executable": executable.name, "updateRunner": runner.name,
                "displayName": "Honsen CAD 翻译器", "publisher": "Honsen",
                "updateManifestUrl": "https://example.test/latest",
            }), encoding="utf-8")
            good = {"AppId": "honsen.cad-translator", "InstallLocation": str(target), "ExecutablePath": str(executable), "UpdateRunnerPath": str(runner), "LauncherPath": str(runner), "UpdateManifestUrl": "https://example.test/latest", "Publisher": "Honsen", "Version": "1.10.0"}
            with patch("desktop.update_runner._registries", return_value=[good]):
                update_runner._validate_target("honsen.cad-translator", target)
            with patch("desktop.update_runner._registries", return_value=[{**good, "InstallLocation": str(target / "other")}]):
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._validate_target("honsen.cad-translator", target)
            for broken in ({**good, "Version": "9.9.9"}, {**good, "LauncherPath": str(target / "other.exe")}):
                with patch("desktop.update_runner._registries", return_value=[broken]), self.assertRaises(update_runner.UpdateFailure):
                    update_runner._validate_target("honsen.cad-translator", target)
            with patch("desktop.update_runner._registries", return_value=[{**good, "Publisher": "Other"}]):
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._validate_target("honsen.cad-translator", target)
            with patch("desktop.update_runner._registries", return_value=[good, {**good, "Publisher": "Other"}]):
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._validate_target("honsen.cad-translator", target)

    @unittest.skipUnless(__import__("sys").platform == "win32", "Windows process APIs required")
    def test_wait_pid_rejects_a_real_unrelated_process(self):
        import subprocess
        import sys
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
        try:
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._wait_for_pid(process.pid, Path(sys.executable).parent / "unrelated.exe")
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            process.wait(timeout=5)

    @unittest.skipUnless(__import__("sys").platform == "win32", "Windows mutex APIs required")
    def test_mutex_excludes_another_process(self):
        import ctypes
        import subprocess
        import sys
        import uuid
        from ctypes import wintypes
        app_id = "test-" + uuid.uuid4().hex
        handle = update_runner._mutex(app_id)
        try:
            code = ("from desktop.update_runner import _mutex, UpdateFailure\n"
                    "try: _mutex(" + repr(app_id) + ")\n"
                    "except UpdateFailure: raise SystemExit(0)\n"
                    "raise SystemExit(1)")
            result = subprocess.run([sys.executable, "-c", code], timeout=10)
            self.assertEqual(result.returncode, 0)
        finally:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.ReleaseMutex.argtypes = (wintypes.HANDLE,)
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)

    def test_wait_pid_checks_path_before_waiting(self):
        class Function:
            def __init__(self, value): self.value = value; self.called = False
            def __call__(self, *args): self.called = True; return self.value
        class Kernel:
            OpenProcess = Function(42)
            WaitForSingleObject = Function(0)
            TerminateProcess = Function(1)
            CloseHandle = Function(1)
        kernel = Kernel()
        with patch("desktop.update_runner.ctypes.WinDLL", return_value=kernel), patch("desktop.update_runner._process_path", return_value="C:\\other.exe"):
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._wait_for_pid(123, Path("C:/expected.exe"))
        self.assertFalse(kernel.WaitForSingleObject.called)

    def test_wait_pid_fails_closed_when_process_access_denied(self):
        class Function:
            def __call__(self, *args): return 0
        class Kernel:
            OpenProcess = Function()
        with patch("desktop.update_runner.ctypes.WinDLL", return_value=Kernel()), patch("desktop.update_runner.ctypes.get_last_error", return_value=5):
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._wait_for_pid(123, Path("app.exe"))

    def test_registry_reads_four_views_and_rejects_damaged_records(self):
        import sys
        import types
        calls = []
        class Key:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        def open_key(root, path, reserved=0, access=0):
            calls.append((root, access))
            raise FileNotFoundError()
        fake = types.SimpleNamespace(HKEY_LOCAL_MACHINE=1, HKEY_CURRENT_USER=2,
                                     KEY_READ=4, KEY_WOW64_32KEY=8, KEY_WOW64_64KEY=16,
                                     OpenKey=open_key)
        with patch.dict(sys.modules, {"winreg": fake}):
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._registries(update_runner.APP_ID)
        self.assertEqual(set(calls), {(1, 12), (1, 20), (2, 12), (2, 20)})
        fake.OpenKey = lambda *args: Key()
        fake.QueryValueEx = lambda key, name: (_ for _ in ()).throw(FileNotFoundError())
        with patch.dict(sys.modules, {"winreg": fake}):
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._registries(update_runner.APP_ID)

    def test_runner_rejects_manifest_path_escape_and_wrong_app_id(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "honsen.app.json").write_text(json.dumps({
                "appId": "honsen.cad-translator", "version": "1.0.0", "executable": "../outside.exe",
                "updateRunner": "HonsenUpdateRunner.exe"}), encoding="utf-8")
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._metadata(target)
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._validate_target("honsen.other", target)

    def test_runner_release_requires_exact_version_and_full_digest(self):
        for payload in (release("1.11.1", name="Honsen_DrawTranslate_v1.11.10_Setup.exe"),
                        {**release(), "assets": [{**release()["assets"][0], "digest": "sha256:abc"}]}):
            with self.subTest(payload=payload), patch("desktop.update_runner.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._release("1.0.0", "https://example.test/latest")

    def test_result_path_rejects_untrusted_app_id(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(update_runner, "RESULTS_DIR", Path(directory)):
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._result_location("../../outside", None, None)

    def test_atomic_result_does_not_overwrite_another_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "operation.json"
            update_runner._write_result(result, {"status": "success"})
            with self.assertRaises(FileExistsError):
                update_runner._write_result(result, {"status": "failed"})
            self.assertEqual(json.loads(result.read_text(encoding="utf-8")), {"status": "success"})

    def test_operation_claim_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(update_runner, "RESULTS_DIR", Path(directory)):
            op, path = update_runner._result_location(update_runner.APP_ID, None, None)
            update_runner._claim_operation(path)
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._claim_operation(path)

    def test_relocated_runner_requires_temp_copy_and_matching_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registered = root / "installed.exe"
            registered.write_bytes(b"trusted")
            relocated = root / "Honsen Program" / "UpdateRunner" / "operation" / "HonsenUpdateRunner.exe"
            relocated.parent.mkdir(parents=True)
            relocated.write_bytes(b"trusted")
            with patch("desktop.update_runner.tempfile.gettempdir", return_value=str(root)):
                update_runner._validate_relocated(relocated, registered)
                relocated.write_bytes(b"tampered")
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._validate_relocated(relocated, registered)
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._validate_relocated(registered, registered)

    @unittest.skipUnless(__import__("sys").platform == "win32", "Windows junctions required")
    def test_result_directory_junction_escape_is_rejected(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results, outside = root / "results", root / "outside"
            results.mkdir()
            outside.mkdir()
            junction = results / update_runner.APP_ID
            created = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True)
            self.assertEqual(created.returncode, 0, created.stderr.decode(errors="replace"))
            with patch.object(update_runner, "RESULTS_DIR", results):
                _, path = update_runner._result_location(update_runner.APP_ID, None, None)
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._claim_operation(path)
            self.assertEqual(list(outside.iterdir()), [])

    def test_manifest_symlink_outside_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            outside = root / "manifest.json"
            outside.write_text("{}", encoding="utf-8")
            try:
                (target / "honsen.app.json").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._metadata(target)

    def test_runner_uses_operation_scoped_result_paths_and_standard_result_fields(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(update_runner, "RESULTS_DIR", Path(directory)):
            first_id, first_path = update_runner._result_location("honsen.cad-translator", "123e4567-e89b-12d3-a456-426614174000", None)
            second_id, second_path = update_runner._result_location("honsen.cad-translator", "123e4567-e89b-12d3-a456-426614174001", None)
            self.assertNotEqual(first_path, second_path)
            self.assertEqual(first_path.name, f"{first_id}.json")
            with self.assertRaises(update_runner.UpdateFailure):
                update_runner._result_location("honsen.cad-translator", first_id, str(Path(directory) / "other.json"))
            result = update_runner._result(type("Args", (), {"app_id": "honsen.cad-translator", "source": "toolbox", "operation_id": first_id})(), "failed", step="sha256", message="校验失败")
            self.assertEqual(set(result), {"appId", "status", "source", "operationId", "fromVersion", "toVersion", "step", "installerExitCode", "installerLogPath", "message"})

    def test_runner_update_choices_stay_in_the_progress_window(self):
        runner = (Path(__file__).resolve().parents[1] / "desktop" / "update_runner.py").read_text(encoding="utf-8")
        self.assertNotIn("messagebox", runner)
        for label in ("立即更新", "稍后提醒", "跳过此版本"):
            self.assertIn(f'text="{label}"', runner)


if __name__ == "__main__":
    unittest.main()
