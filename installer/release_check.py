"""Check CAD release identity before packaging or publication."""
import argparse
import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_versions(versions):
    version = versions["manifest"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("invalid manifest version")
    for name, value in versions.items():
        required = ("v" + version if name == "tag" else
                    f"Honsen_DrawTranslate_v{version}_Setup.exe" if name == "asset" else version)
        if value != required:
            raise ValueError(f"{name} mismatch: {value} != {required}")



def normalize_setup_version(value):
    match = re.fullmatch(r"([0-9]+\.[0-9]+\.[0-9]+)(?:\.0)?", value.strip())
    if not match:
        raise ValueError("invalid setup file version")
    return match.group(1)


def validate_release(release, version, digest):
    name = f"Honsen_DrawTranslate_v{version}_Setup.exe"
    if release.get("draft") or release.get("prerelease") or release.get("tag_name") != "v" + version:
        raise ValueError("release tag or status mismatch")
    assets = release.get("assets", [])
    installers = [a for a in assets if a.get("name", "").lower().endswith(".exe")]
    if len(installers) != 1 or installers[0].get("name") != name:
        raise ValueError("release must contain the expected single installer")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", digest) or installers[0].get("digest", "").lower() != "sha256:" + digest.lower():
        raise ValueError("GitHub API digest mismatch")
    if sum(a.get("name") == name + ".sha256" for a in assets) != 1:
        raise ValueError("release checksum asset missing")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe-version", required=True)
    parser.add_argument("--product-version")
    parser.add_argument("--setup-version")
    parser.add_argument("--tag")
    parser.add_argument("--release-json", type=Path)
    parser.add_argument("--setup", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "honsen.app.json").read_text(encoding="utf-8"))
    script = (ROOT / "installer/Honsen_DrawTranslate_Setup.iss").read_text(encoding="utf-8")
    match = re.search(r'^#define MyAppVersion "([^"]+)"$', script, re.MULTILINE)
    if not match:
        raise ValueError("missing installer version")
    build = (ROOT / "installer/build_installer.ps1").read_text(encoding="utf-8-sig")
    asset = re.search(r'installer\\Output\\(Honsen_DrawTranslate_v[^"\\]+_Setup\.exe)', build)
    if not asset:
        raise ValueError("missing build asset name")
    versions = {"manifest": manifest["version"], "installer": match.group(1),
                "exe": args.exe_version, "asset": asset.group(1)}
    sources = {
        "backend": ("backend/updater.py", r'^CURRENT_VERSION = "([^"]+)"'),
        "translator": ("backend/translator.py", r'^APP_VERSION = "([^"]+)"'),
        "frontend_ui": ("frontend/src/App.jsx", r'^const APP_VERSION = "([^"]+)"'),
        "desktop_title": ("desktop/launcher.py", r'^TITLE = ".* v([0-9.]+)"'),
        "resource_file": ("Honsen_DrawTranslate_version_info.txt", r"StringStruct\('FileVersion', '([^']+)'\)"),
        "resource_product": ("Honsen_DrawTranslate_version_info.txt", r"StringStruct\('ProductVersion', '([^']+)'\)"),
    }
    for name, (path, pattern) in sources.items():
        source = (ROOT / path).read_text(encoding="utf-8-sig")
        match = re.search(pattern, source, re.MULTILINE)
        if not match:
            raise ValueError(f"missing {name} version")
        versions[name] = match.group(1)
    for name, path in (("frontend", "frontend/package.json"), ("frontend_lock", "frontend/package-lock.json")):
        versions[name] = json.loads((ROOT / path).read_text(encoding="utf-8"))["version"]
    if args.product_version:
        versions["product"] = args.product_version
    if args.setup_version:
        versions["setup"] = normalize_setup_version(args.setup_version)
    if args.tag:
        versions["tag"] = args.tag
    validate_versions(versions)
    if args.release_json or args.setup:
        if not (args.release_json and args.setup and args.tag):
            raise ValueError("release validation requires --tag, --release-json and --setup")
        if args.setup.name != versions["asset"]:
            raise ValueError("setup filename mismatch")
        digest = hashlib.sha256(args.setup.read_bytes()).hexdigest()
        sidecar = Path(str(args.setup) + ".sha256")
        if sidecar.read_text(encoding="ascii").split()[0].lower() != digest:
            raise ValueError("local sidecar mismatch")
        validate_release(json.loads(args.release_json.read_text(encoding="utf-8-sig")), versions["manifest"], digest)
    print("Release versions match:", versions["manifest"])


if __name__ == "__main__":
    main()
