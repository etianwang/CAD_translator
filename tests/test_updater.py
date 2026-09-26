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


def release(version="1.9.6", *, digest=True, prerelease=False, name=None):
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
        self.assertEqual(update["latest_version"], "1.9.6")

    def test_invalid_or_non_newer_releases_are_refused(self):
        for payload in (
            release("1.9.4"),
            release("1.9.6", prerelease=True),
            release("1.9.6", digest=False),
            release("1.9.6", name="HonsenCAD.v1.9.exe"),
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

    def test_windows_only_launches_a_verified_installer_name(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory) / "HonsenCAD.v1.9.4.exe"
            installer.write_bytes(b"installer")
            with (
                patch("desktop.native_bridge.sys.platform", "win32"),
                patch("desktop.native_bridge.subprocess.Popen") as popen,
                patch("desktop.native_bridge.threading.Timer") as timer,
            ):
                self.assertEqual(NativeBridge().install_update(str(installer)), {"ok": True})
            self.assertIn("/VERYSILENT", popen.call_args.args[0])
            timer.assert_called_once()

        self.assertIn("自动更新仅支持", NativeBridge().install_update("missing.exe")["error"])

    def test_existing_honsencad_installer_name_is_accepted(self):
        with patch("backend.updater.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release(name="HonsenCAD.v1.9.6.exe")).encode())):
            self.assertTrue(updater.check_for_update()["available"])

    def test_inno_setup_restarts_after_a_silent_update(self):
        script = (Path(__file__).resolve().parents[1] / "installer" / "Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
        run_line = next(line for line in script.splitlines() if line.startswith('Filename: "{app}\\{#MyAppExeName}"; Description:'))
        self.assertIn("runasoriginaluser", run_line)
        self.assertNotIn("postinstall", run_line)
        self.assertNotIn("skipifsilent", run_line)


if __name__ == "__main__":
    unittest.main()
