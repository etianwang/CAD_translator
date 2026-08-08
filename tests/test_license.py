"""No-network checks for trial expiry and signed activation codes."""

import base64
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend import licensing as license_manager
from backend.licensing import LicenseManager
from backend.api import support_info


def encode(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


license_manager.LICENSE_ENFORCEMENT_ENABLED = True
assert support_info()["licensing_enabled"] is False  # packaged default is the non-commercial build

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    private = Ed25519PrivateKey.generate()
    public = root / "public.txt"
    public.write_text(encode(private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)), encoding="utf-8")
    now = datetime(2026, 8, 8, tzinfo=timezone.utc)
    manager = LicenseManager(root / "license.json", public)
    with patch("backend.licensing._network_now", return_value=now):
        trial = manager.status()
        assert trial["usable"] and trial["expires_on"] == "2026-09-06"
        payload = encode(json.dumps({"v": 1, "expires_on": "2026-09-30", "plan": "季卡"}, separators=(",", ":")).encode())
        code = f"{payload}.{encode(private.sign(payload.encode()))}"
        activated = manager.activate(code)
        assert activated["usable"] and activated["expires_on"] == "2026-09-30"
        renewed_payload = encode(json.dumps({"v": 1, "expires_on": "2027-08-08", "plan": "续费一年"}, separators=(",", ":")).encode())
        renewed = manager.activate(f"{renewed_payload}.{encode(private.sign(renewed_payload.encode()))}")
        assert renewed["usable"] and renewed["expires_on"] == "2027-08-08"
    expired = LicenseManager(root / "expired.json", public)
    with patch("backend.licensing._network_now", return_value=datetime(2026, 10, 1, tzinfo=timezone.utc)):
        assert not expired.activate(code)["usable"]
    with patch("backend.licensing.LICENSE_ENFORCEMENT_ENABLED", False), patch("backend.licensing._network_now", side_effect=AssertionError("must not sync")):
        assert LicenseManager(root / "disabled.json", public).status()["state"] == "disabled"
