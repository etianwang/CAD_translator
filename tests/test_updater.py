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


def release(version="1.11.3", *, digest=True, prerelease=False, name=None):
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
    def test_only_newer_checksums_installer_is_offered(self):
        with patch("backend.updater.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release()).encode())):
            update = updater.check_for_update()
        self.assertTrue(update["available"])
        self.assertEqual(update["latest_version"], "1.11.3")

    def test_invalid_or_non_newer_releases_are_refused(self):
        for payload in (
            release("1.9.4"),
            release("1.9.8"),
            release("1.11.3", prerelease=True),
            release("1.11.3", digest=False),
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
                self.assertEqual(NativeBridge().install_update(str(installer), "a" * 64, "1.10.1"), {"ok": True})
            command = popen.call_args.args[0]
            self.assertEqual(Path(command[0]).resolve(), runner.resolve())
            self.assertEqual(command[1:3], ["apply", "--source"])
            self.assertIn("--wait-pid", command)
            self.assertEqual(Path(command[command.index("--target-dir") + 1]).resolve(), app_dir.resolve())
            thread.assert_called_once()

        self.assertIn("更新助手", NativeBridge().install_update("missing.exe", "", "")["error"])

    def test_existing_honsencad_installer_name_is_accepted(self):
        with patch("backend.updater.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release(name="HonsenCAD.v1.11.3.exe")).encode())):
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
        self.assertIn('Name: "{app}\\Honsen DrawTranslate v*.exe"', script)
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
        self.assertIn('ValueName: "UpdateUrl"; ValueData: "{#MyHonsenUpdateURL}"', script)
        self.assertIn('ValueData: "{#MyHonsenAppId}"; Flags: uninsdeletekey', script)

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
        self.assertIn('"--sha256", sha256', bridge)
        runner = (root / "desktop" / "update_runner.py").read_text(encoding="utf-8")
        self.assertIn('"Honsen Program" / "UpdateRunner"', runner)
        self.assertIn('"--relocated"', runner)
        self.assertIn('"status": "success"', runner)

    def test_runner_rejects_mismatched_registry_or_manifest_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            executable = target / "Honsen DrawTranslate.exe"
            runner = target / "HonsenUpdateRunner.exe"
            executable.write_bytes(b"app")
            runner.write_bytes(b"runner")
            (target / "honsen.app.json").write_text(json.dumps({
                "appId": "honsen.cad-translator", "version": "1.10.0",
                "executableName": executable.name, "updateRunnerName": runner.name,
            }), encoding="utf-8")
            good = {"AppId": "honsen.cad-translator", "InstallLocation": str(target), "ExecutablePath": str(executable), "UpdateRunnerPath": str(runner), "UpdateManifestUrl": "https://example.test/latest", "Version": "1.10.0"}
            with patch("desktop.update_runner._registries", return_value=[good]):
                update_runner._validate_target("honsen.cad-translator", target)
            with patch("desktop.update_runner._registries", return_value=[{**good, "InstallLocation": str(target / "other")}]):
                with self.assertRaises(update_runner.UpdateFailure):
                    update_runner._validate_target("honsen.cad-translator", target)


if __name__ == "__main__":
    unittest.main()
